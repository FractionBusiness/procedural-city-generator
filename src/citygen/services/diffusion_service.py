"""Block-fill diffusion service.

Loads an ONNX block-diffuser checkpoint (or falls back to a procedural
noise fill if the checkpoint is missing) and stamps building footprints
into each block polygon. Batch size is honored; tiles are 512px by default.

* onnxruntime >= 1.18 required for the DML execution provider on Windows;
  the CUDA EP is not built into the default PyPI wheel.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from loguru import logger

from citygen.core.types import BlockSpec, DiffusionConfig


class DiffusionService:
    def __init__(self, config: DiffusionConfig) -> None:
        self.config = config
        self._session = None

    def _load(self) -> None:
        ckpt = Path(self.config.checkpoint)
        if not ckpt.exists():
            logger.warning("checkpoint {} missing — using procedural fallback", ckpt)
            return
        import onnxruntime as ort

        providers = ["CPUExecutionProvider"]
        if self.config.device in ("auto", "dml"):
            available = ort.get_available_providers()
            if "DmlExecutionProvider" in available:
                providers.insert(0, "DmlExecutionProvider")
        self._session = ort.InferenceSession(str(ckpt), providers=providers)
        logger.info("diffusion session ready — providers={}", self._session.get_providers())

    def fill(self, blocks: list[BlockSpec]) -> list[BlockSpec]:
        if self._session is None:
            self._load()
        if self._session is None:
            return self._procedural_fill(blocks)

        out: list[BlockSpec] = []
        batch = self.config.batch
        for start in range(0, len(blocks), batch):
            chunk = blocks[start : start + batch]
            latents = np.stack([self._encode(b) for b in chunk]).astype(np.float32)
            for _ in range(self.config.steps):
                latents = self._denoise_step(latents)
            for b, lat in zip(chunk, latents, strict=True):
                out.append(self._stamp(b, lat))
        return out

    def _encode(self, block: BlockSpec) -> np.ndarray:
        pts = block.footprint
        c = pts.mean(axis=0)
        return np.concatenate([c, pts.std(axis=0)]).astype(np.float32)

    def _denoise_step(self, latents: np.ndarray) -> np.ndarray:
        assert self._session is not None
        name = self._session.get_inputs()[0].name
        out = self._session.run(None, {name: latents})[0]
        return latents * 0.85 + out * 0.15 * self.config.guidance / 6.5

    def _stamp(self, block: BlockSpec, latent: np.ndarray) -> BlockSpec:
        # Height modulated by latent magnitude; keeps the block identity intact.
        height = float(np.clip(np.abs(latent).mean() * 40.0, 4.0, 180.0))
        return BlockSpec(
            block_id=block.block_id,
            footprint=block.footprint,
            zoning=block.zoning,
            density=block.density,
            height_m=height,
        )

    def _procedural_fill(self, blocks: list[BlockSpec]) -> list[BlockSpec]:
        rng = np.random.default_rng(0xC17)
        return [
            BlockSpec(
                block_id=b.block_id,
                footprint=b.footprint,
                zoning=b.zoning,
                density=b.density,
                height_m=float(rng.uniform(6, 120)),
            )
            for b in blocks
        ]