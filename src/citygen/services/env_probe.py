"""`citygen doctor` — verify runtime deps, GPU providers, and checkpoints."""
from __future__ import annotations

import platform
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def run_doctor() -> int:
    table = Table(title="procedural-city-generator — doctor")
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail")

    table.add_row("python", "ok", sys.version.split()[0])
    table.add_row("platform", "ok", f"{platform.system()} {platform.release()}")

    try:
        import onnxruntime as ort
        providers = ", ".join(ort.get_available_providers())
        table.add_row("onnxruntime", "ok", ort.__version__)
        table.add_row("exec providers", "ok", providers)
    except ImportError as exc:
        table.add_row("onnxruntime", "MISSING", str(exc))

    try:
        import torch
        table.add_row("torch", "ok", torch.__version__)
    except ImportError:
        table.add_row("torch", "optional", "not installed (CPU-only mode)")

    ckpt = Path("models/checkpoints/block_diffuser_v3.onnx")
    table.add_row("checkpoint", "ok" if ckpt.exists() else "MISSING", str(ckpt))

    console.print(table)
    return 0