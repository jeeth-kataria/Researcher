"""Explicit live Groq connectivity probe. Consumes free quota if successful; not research."""

import json
import sys
from rgi.config import settings
from rgi.provider import Groq


def main():
    config = settings()
    result = {
        "provider": "groq",
        "model": config.groq_model,
        "key_configured": bool(config.groq_api_key),
        "free_plan_acknowledged": config.free_tier_ack,
        "research_run": False,
    }
    try:
        generator = Groq()
        _, tokens, usage = generator.generate(
            "plan",
            'Connectivity probe only. Return summary="Connection verified" and empty '
            "lists for all remaining fields. No research claims or tool use.",
            {},
            800,
        )
        result.update(status="success", structured_output_valid=True, total_tokens=tokens, usage=usage)
    except Exception as exc:
        types = []
        current = exc
        while current is not None and len(types) < 8:
            types.append(type(current).__name__)
            current = current.__cause__ or current.__context__
        result.update(status="failed", exception_types=types)
        if "gaierror" in types:
            result["explanation"] = "DNS resolution failed before Groq could receive the request."
        elif "APIConnectionError" in types:
            result["explanation"] = "No provider response received; inspect local network/proxy access."
        else:
            result["explanation"] = "Configuration, quota or response check failed; raw details omitted to protect credentials."
        print(json.dumps(result, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
