"""Allowlisted job runners — no arbitrary shell from Discord."""

from __future__ import annotations

import platform
import time
from typing import Any, Callable

import json

from gpu_swarm import ALLOWED_JOB_TYPES, MAX_RESULT_BYTES
from gpu_swarm.gpu import inventory_summary, query_gpus
from gpu_swarm.host_protect import clamp_cuda_matrix_size, evaluate_admission, load_host_protect
from gpu_swarm.llm_runtime import ENABLE_LLM_HELP, chat_completions, detect_llm_runtime


def run_probe(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Real GPU probe via nvidia-smi — proves network + worker path."""
    inv = inventory_summary()
    return {
        "job_type": "probe",
        "platform": platform.platform(),
        "hostname": platform.node(),
        "timestamp": time.time(),
        "inventory": inv,
        "payload_echo": payload or {},
    }


def run_pytorch_cuda_probe(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Small real CUDA tensor op when torch+CUDA available; else clear CPU fallback note."""
    payload = payload or {}
    protect = load_host_protect()
    # Accept matrix_size (CLI/SDK) or size (portal Utilize panel)
    raw_size = payload.get("matrix_size", payload.get("size", 1024))
    try:
        size = int(raw_size or 1024)
    except (TypeError, ValueError):
        size = 1024
    size = clamp_cuda_matrix_size(size, protect)
    device_index = payload.get("device_index")
    started = time.time()
    gpus = query_gpus()

    # Refuse to peg the host GPU when desktop headroom is already gone.
    admission = evaluate_admission(gpus, protect)
    if protect.enabled and gpus and not admission.admit:
        raise RuntimeError(
            "host_protect blocked pytorch_cuda_probe: "
            f"{admission.reason}. Wait for GPU util/VRAM headroom or set "
            "GPU_SWARM_HOST_PROTECT=0 (not recommended on a desktop host)."
        )

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "torch not installed on this worker. Install CUDA torch to run pytorch_cuda_probe."
        ) from exc

    cuda_ok = bool(torch.cuda.is_available())
    device_count = torch.cuda.device_count() if cuda_ok else 0
    device_names = []
    if cuda_ok:
        for i in range(device_count):
            device_names.append(torch.cuda.get_device_name(i))

    if not cuda_ok or device_count == 0:
        # Still do a small CPU matmul so the job completes meaningfully.
        a = __import__("torch").randn(size, size)
        b = __import__("torch").randn(size, size)
        c = a @ b
        checksum = float(c.sum().item())
        return {
            "job_type": "pytorch_cuda_probe",
            "cuda_available": False,
            "used_device": "cpu",
            "matrix_size": size,
            "checksum": checksum,
            "elapsed_sec": round(time.time() - started, 4),
            "nvidia_smi_gpus": gpus,
            "note": "CUDA not available to torch; ran CPU matmul",
            "torch_version": getattr(torch, "__version__", "unknown"),
            "host_protect": protect.summary(),
        }

    # Prefer a free-enough GPU; allow caller override.
    idx = int(device_index) if device_index is not None else _pick_gpu(gpus, device_count)
    device = torch.device(f"cuda:{idx}")
    # Warmup + timed matmul
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)
    torch.cuda.synchronize(device)
    t0 = time.time()
    c = a @ b
    torch.cuda.synchronize(device)
    elapsed = time.time() - t0
    checksum = float(c.sum().item())
    mem = torch.cuda.memory_allocated(device)
    return {
        "job_type": "pytorch_cuda_probe",
        "cuda_available": True,
        "used_device": f"cuda:{idx}",
        "device_name": torch.cuda.get_device_name(idx),
        "device_names": device_names,
        "matrix_size": size,
        "checksum": checksum,
        "matmul_sec": round(elapsed, 4),
        "elapsed_sec": round(time.time() - started, 4),
        "memory_allocated_bytes": mem,
        "nvidia_smi_gpus": gpus,
        "torch_version": getattr(torch, "__version__", "unknown"),
        "host_protect": protect.summary(),
    }


def _pick_gpu(gpus: list[dict[str, Any]], device_count: int) -> int:
    """Pick GPU with most free VRAM among torch-visible devices."""
    best_idx = 0
    best_free = -1
    for g in gpus:
        idx = int(g.get("index", 0))
        if idx >= device_count:
            continue
        free = int(g.get("memory_free_mb", 0))
        if free > best_free:
            best_free = free
            best_idx = idx
    return best_idx


def run_llm_chat(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Chat via worker-local Ollama / OpenAI-compatible runtime (allowlisted).

    Payload: model, messages, max_tokens (optional temperature).
    """
    payload = payload or {}
    model = str(payload.get("model") or "").strip() or "llama3.2"
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("llm_chat requires a non-empty messages list")
    clean_msgs: list[dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "user")
        content = m.get("content")
        if content is None:
            continue
        clean_msgs.append({"role": role, "content": content})
    if not clean_msgs:
        raise ValueError("llm_chat messages must include role/content")

    raw_max = payload.get("max_tokens", 512)
    try:
        max_tokens = int(raw_max or 512)
    except (TypeError, ValueError):
        max_tokens = 512
    max_tokens = max(1, min(max_tokens, 8192))

    temperature = payload.get("temperature")
    if temperature is not None:
        try:
            temperature = float(temperature)
        except (TypeError, ValueError):
            temperature = None

    rt = detect_llm_runtime(timeout=2.0)
    if not rt.get("ready"):
        raise RuntimeError(ENABLE_LLM_HELP + f"\n(last probe: {rt.get('error')})")

    if not model or model in ("gpu-pool", "gpu-pool/auto", "local-pool"):
        models = rt.get("models") or []
        model = str(models[0]) if models else "llama3.2"

    started = time.time()
    completion = chat_completions(
        model=model,
        messages=clean_msgs,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=300.0,
        runtime=rt,
    )
    meta = completion.pop("_gpu_pool_runtime", None) or {}
    assistant_text = _assistant_text(completion)
    if not assistant_text.strip():
        raise RuntimeError(
            "LLM runtime completed without final assistant text; the model exhausted its "
            "generation budget in internal reasoning or returned an empty response. "
            "Retry with a larger output budget or choose another mounted chat model."
        )
    raw = json.dumps(completion)
    if len(raw.encode("utf-8")) > MAX_RESULT_BYTES - 2000:
        choices = completion.get("choices") or []
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message") or {}
            content = str(msg.get("content") or "")
            budget = max(500, (MAX_RESULT_BYTES // 2) - 500)
            if len(content) > budget:
                msg = dict(msg)
                msg["content"] = content[:budget] + "\n…[truncated by gpu-swarm MAX_RESULT_BYTES]"
                choices = list(choices)
                choices[0] = {**choices[0], "message": msg}
                completion = {**completion, "choices": choices, "truncated": True}

    return {
        "job_type": "llm_chat",
        "platform": platform.platform(),
        "hostname": platform.node(),
        "elapsed_sec": round(time.time() - started, 4),
        "runtime": meta,
        "model": model,
        "completion": completion,
        "message": _assistant_text(completion),
    }


def _assistant_text(completion: dict[str, Any]) -> str:
    choices = completion.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    msg = choices[0].get("message") or {}
    return str(msg.get("content") or "") if isinstance(msg, dict) else ""


RUNNERS: dict[str, Callable[[dict[str, Any] | None], dict[str, Any]]] = {
    "probe": run_probe,
    "pytorch_cuda_probe": run_pytorch_cuda_probe,
    "llm_chat": run_llm_chat,
}


def execute_job(job_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if job_type not in ALLOWED_JOB_TYPES:
        raise ValueError(f"job type not allowlisted: {job_type}")
    runner = RUNNERS.get(job_type)
    if not runner:
        raise ValueError(f"no runner for job type: {job_type}")
    return runner(payload)
