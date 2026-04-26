"""Edge-Deployment Konfiguration — Whisper lokal auf Konferenz-Server.

Für Live-Meetings: minimale Latenz durch lokales Whisper-Modell.
Kein Netzwerk-Roundtrip für ASR — Audio bleibt im lokalen Netzwerk.

Konfiguriert über Umgebungsvariablen:
  WHISPER_MODEL: base | small | medium | large-v3
  WHISPER_DEVICE: cpu | cuda
  WHISPER_COMPUTE: int8 | float16 | float32
  EDGE_MODE: true | false
"""
from __future__ import annotations

import os

# Edge-Mode Konfiguration
EDGE_MODE = os.environ.get("EDGE_MODE", "false").lower() == "true"
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.environ.get("WHISPER_COMPUTE", "int8")

# Modell-Empfehlungen nach Hardware
MODEL_RECOMMENDATIONS = {
    "raspberry_pi": {"model": "base", "device": "cpu", "compute": "int8", "ram": "2GB"},
    "office_pc": {"model": "small", "device": "cpu", "compute": "int8", "ram": "4GB"},
    "workstation": {"model": "medium", "device": "cpu", "compute": "float16", "ram": "8GB"},
    "gpu_server": {"model": "large-v3", "device": "cuda", "compute": "float16", "ram": "16GB"},
}

# Latenz-Erwartungen (pro 3s Audio-Chunk)
LATENCY_ESTIMATES = {
    "base_cpu_int8": "~300ms",
    "small_cpu_int8": "~600ms",
    "medium_cpu_float16": "~1200ms",
    "large-v3_cuda_float16": "~200ms",
}


def get_edge_config() -> dict:
    """Get current edge deployment configuration."""
    return {
        "edge_mode": EDGE_MODE,
        "model": WHISPER_MODEL,
        "device": WHISPER_DEVICE,
        "compute_type": WHISPER_COMPUTE,
        "estimated_latency": LATENCY_ESTIMATES.get(
            f"{WHISPER_MODEL}_{WHISPER_DEVICE}_{WHISPER_COMPUTE}",
            "unknown"
        ),
        "recommendations": MODEL_RECOMMENDATIONS,
    }
