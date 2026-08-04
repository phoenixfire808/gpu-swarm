"""gpu-swarm — private Discord GPU/CPU contribution pool."""

__version__ = "0.1.0"

# Allowlisted job types workers may execute (no arbitrary shell).
ALLOWED_JOB_TYPES = frozenset({"probe", "pytorch_cuda_probe"})

# Cap result payloads returned to scheduler / Discord (bytes of JSON text).
MAX_RESULT_BYTES = 64_000
