from rgi.db import checkpoints

with checkpoints() as saver:
    saver.setup()
print("PostgreSQL graph checkpoint schema ready")
