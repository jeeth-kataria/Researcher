"""In-memory graph UNIT tests, explicitly not PostgreSQL integration substitutes."""

from rgi.research import build_graph


def test_graph_order_and_restart():
    from langgraph.checkpoint.memory import InMemorySaver

    class Stages:
        run = {"mode": "multi"}

        def __init__(self):
            self.calls = []
            self.crash = True

        def retrieve(self, state):
            self.calls.append("retrieve")
            return {"queries": ["memory"], "completed": ["retrieve"]}

        def role(self, role, state):
            if role == "review" and self.crash:
                self.crash = False
                raise RuntimeError("Simulated process interruption")
            self.calls.append(role)
            return {"completed": state["completed"] + [role]}

        def finalize(self, state):
            self.calls.append("report")
            return {"completed": state["completed"] + ["report"]}

    stages = Stages()
    graph = build_graph(stages, InMemorySaver())
    config = {"configurable": {"thread_id": "unit-only"}}
    import pytest

    with pytest.raises(RuntimeError):
        graph.invoke({"run_id": "unit"}, config)
    result = graph.invoke(None, config)
    assert stages.calls == [
        "retrieve",
        "plan",
        "literature",
        "methods",
        "candidates",
        "review",
        "experiments",
        "report",
    ]
    assert result["completed"][-1] == "report"
