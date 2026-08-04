"""gpu-swarm — private Discord GPU/CPU contribution pool."""

__version__ = "0.1.1"

# Allowlisted job types workers may execute (no arbitrary shell).
ALLOWED_JOB_TYPES = frozenset({"probe", "pytorch_cuda_probe", "llm_chat"})

# Cap result payloads returned to scheduler / Discord (bytes of JSON text).
# llm_chat truncates assistant text to stay under this.
MAX_RESULT_BYTES = 96_000

from gpu_swarm.client import DEFAULT_SCHEDULER_URL, GPUPool, GPUPoolError  # noqa: E402

__all__ = [
    "ALLOWED_JOB_TYPES",
    "DEFAULT_SCHEDULER_URL",
    "GPUPool",
    "GPUPoolError",
    "MAX_RESULT_BYTES",
    "__version__",
]

# Alias: from gpu_swarm import gpu_pool  /  import gpu_swarm; gpu_swarm.gpu_pool
gpu_pool = GPUPool
