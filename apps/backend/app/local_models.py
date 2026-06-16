"""Local open-weight model management via Ollama.

Ollama is the integration point deliberately: it already solves download,
checksumming, quantization selection, GPU/CPU fallback, and serves an
OpenAI-compatible API — the platform passes through rather than reimplementing
any of that. Only models on the curated catalog below may be pulled
(allowlist; arbitrary registry pulls are rejected).
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Any

# Curated pick list. Sizes are approximate download sizes for the default
# quantization; min_ram_gb is a practical host-memory guide for CPU inference.
LOCAL_MODEL_CATALOG: list[dict[str, Any]] = [
    {
        "id": "qwen2.5:0.5b",
        "label": "Qwen 2.5 0.5B (tiny)",
        "family": "Qwen",
        "size_gb": 0.4,
        "min_ram_gb": 4,
        "notes": "Smallest footprint; smoke tests and constrained hosts.",
    },
    {
        "id": "llama3.2:1b",
        "label": "Llama 3.2 1B",
        "family": "Meta Llama",
        "size_gb": 1.3,
        "min_ram_gb": 4,
        "notes": "Very fast on CPU; light assistant tasks.",
    },
    {
        "id": "llama3.2:3b",
        "label": "Llama 3.2 3B",
        "family": "Meta Llama",
        "size_gb": 2.0,
        "min_ram_gb": 8,
        "notes": "Good default for local-first assistants.",
    },
    {
        "id": "llama3.1:8b",
        "label": "Llama 3.1 8B",
        "family": "Meta Llama",
        "size_gb": 4.9,
        "min_ram_gb": 16,
        "notes": "Strong general model; 16 GB+ host or GPU recommended.",
    },
    {
        "id": "qwen2.5:7b",
        "label": "Qwen 2.5 7B",
        "family": "Qwen",
        "size_gb": 4.7,
        "min_ram_gb": 16,
        "notes": "Strong multilingual generalist.",
    },
    {
        "id": "qwen2.5-coder:7b",
        "label": "Qwen 2.5 Coder 7B",
        "family": "Qwen",
        "size_gb": 4.7,
        "min_ram_gb": 16,
        "notes": "Code-focused variant.",
    },
    {
        "id": "mistral:7b",
        "label": "Mistral 7B",
        "family": "Mistral",
        "size_gb": 4.1,
        "min_ram_gb": 16,
        "notes": "Efficient generalist.",
    },
    {
        "id": "gemma2:9b",
        "label": "Gemma 2 9B",
        "family": "Google Gemma",
        "size_gb": 5.4,
        "min_ram_gb": 16,
        "notes": "Strong quality for size.",
    },
    {
        "id": "deepseek-r1:8b",
        "label": "DeepSeek R1 8B",
        "family": "DeepSeek",
        "size_gb": 5.2,
        "min_ram_gb": 16,
        "notes": "Reasoning-tuned distillation.",
    },
    {
        "id": "gpt-oss:20b",
        "label": "GPT-OSS 20B",
        "family": "OpenAI GPT-OSS",
        "size_gb": 13.0,
        "min_ram_gb": 16,
        "notes": "OpenAI open-weight reasoning model (MXFP4); fits 16 GB hosts or a single consumer GPU.",
    },
    {
        "id": "gpt-oss:120b",
        "label": "GPT-OSS 120B",
        "family": "OpenAI GPT-OSS",
        "size_gb": 65.0,
        "min_ram_gb": 80,
        "notes": "OpenAI open-weight flagship; needs ~80 GB (datacenter GPU or very large host).",
    },
]

_CATALOG_IDS = {str(item["id"]) for item in LOCAL_MODEL_CATALOG}

# Pull state per model id. Mutated only under _PULL_LOCK.
_PULLS: dict[str, dict[str, Any]] = {}
_PULL_LOCK = threading.Lock()


# Runtime override (set from platform settings); takes precedence over env.
_BASE_URL_OVERRIDE = ""


def set_base_url_override(value: str) -> None:
    global _BASE_URL_OVERRIDE  # noqa: PLW0603
    _BASE_URL_OVERRIDE = str(value or "").strip().rstrip("/")


def ollama_base_url() -> str:
    if _BASE_URL_OVERRIDE:
        return _BASE_URL_OVERRIDE
    return str(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).strip().rstrip("/")


def ollama_openai_base_url() -> str:
    return f"{ollama_base_url()}/v1"


def _request_json(
    path: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: float = 5.0
) -> Any:
    request = urllib.request.Request(
        f"{ollama_base_url()}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured internal endpoint
        return json.loads(response.read().decode("utf-8", errors="replace") or "{}")


def ollama_available() -> bool:
    try:
        _request_json("/api/version", timeout=3.0)
        return True
    except Exception:  # noqa: BLE001
        return False


def installed_models() -> list[dict[str, Any]]:
    try:
        payload = _request_json("/api/tags", timeout=5.0)
    except Exception:  # noqa: BLE001
        return []
    models = payload.get("models") if isinstance(payload, dict) else None
    results: list[dict[str, Any]] = []
    for item in models or []:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "id": str(item.get("name") or item.get("model") or ""),
                "size_bytes": int(item.get("size") or 0),
                "modified_at": str(item.get("modified_at") or ""),
            }
        )
    return [item for item in results if item["id"]]


def is_catalog_model(model_id: str) -> bool:
    return str(model_id or "").strip() in _CATALOG_IDS


def pull_states() -> dict[str, dict[str, Any]]:
    with _PULL_LOCK:
        return {model_id: dict(state) for model_id, state in _PULLS.items()}


def _run_pull(model_id: str) -> None:
    request = urllib.request.Request(
        f"{ollama_base_url()}/api/pull",
        data=json.dumps({"model": model_id, "stream": True}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        # Model downloads are multi-GB; the stream emits JSON progress lines.
        with urllib.request.urlopen(request, timeout=3600) as response:  # noqa: S310
            for raw_line in response:
                try:
                    line = json.loads(raw_line.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:
                    continue
                if not isinstance(line, dict):
                    continue
                error = str(line.get("error") or "")
                if error:
                    raise RuntimeError(error)
                total = int(line.get("total") or 0)
                completed = int(line.get("completed") or 0)
                with _PULL_LOCK:
                    state = _PULLS.setdefault(model_id, {})
                    state["status"] = "downloading"
                    state["detail"] = str(line.get("status") or "")
                    if total > 0:
                        state["progress_percent"] = round(min(100.0, completed * 100.0 / total), 1)
        with _PULL_LOCK:
            _PULLS[model_id] = {
                "status": "ready",
                "detail": "Model installed.",
                "progress_percent": 100.0,
                "finished_at": time.time(),
            }
    except Exception as exc:  # noqa: BLE001
        with _PULL_LOCK:
            _PULLS[model_id] = {
                "status": "error",
                "detail": str(exc)[:300],
                "progress_percent": _PULLS.get(model_id, {}).get("progress_percent", 0.0),
                "finished_at": time.time(),
            }


def start_pull(model_id: str) -> dict[str, Any]:
    """Begin downloading a catalog model. Returns the initial pull state.

    Raises ValueError for non-catalog models (allowlist) and RuntimeError when
    the Ollama runtime is unreachable.
    """
    normalized = str(model_id or "").strip()
    if not is_catalog_model(normalized):
        raise ValueError("Model is not on the approved local-model catalog")
    if not ollama_available():
        raise RuntimeError("Local model runtime (Ollama) is not reachable")
    with _PULL_LOCK:
        current = _PULLS.get(normalized)
        if current and current.get("status") == "downloading":
            return dict(current)
        _PULLS[normalized] = {
            "status": "downloading",
            "detail": "Starting download...",
            "progress_percent": 0.0,
            "started_at": time.time(),
        }
        state = dict(_PULLS[normalized])
    worker = threading.Thread(
        target=_run_pull, args=(normalized,), name=f"ollama-pull-{normalized}", daemon=True
    )
    worker.start()
    return state


def delete_model(model_id: str) -> bool:
    normalized = str(model_id or "").strip()
    if not is_catalog_model(normalized):
        raise ValueError("Model is not on the approved local-model catalog")
    try:
        request = urllib.request.Request(
            f"{ollama_base_url()}/api/delete",
            data=json.dumps({"model": normalized}).encode("utf-8"),
            method="DELETE",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=30):  # noqa: S310
            pass
        with _PULL_LOCK:
            _PULLS.pop(normalized, None)
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise
