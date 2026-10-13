"""Zoning assignment. Weighted categorical draw biased by distance-to-center,
so density falls off from the core like a real city."""
from __future__ import annotations

import numpy as np

from citygen.core.types import BlockSpec, ZoningConfig
from citygen.utils.geometry import polygon_centroid


class ZoningHandler:
    def __init__(self, config: ZoningConfig, rng: np.random.Generator) -> None:
        self.config = config
        self.rng = rng

    def assign(self, blocks: list[BlockSpec]) -> list[BlockSpec]:
        if not blocks:
            return blocks

        centroids = np.stack([polygon_centroid(b.footprint) for b in blocks])
        center = centroids.mean(axis=0)
        radii = np.linalg.norm(centroids - center, axis=1)
        max_r = float(radii.max()) or 1.0
        norm_r = radii / max_r  # 0 at core, 1 at edge

        base = np.array(
            [self.config.residential, self.config.commercial,
             self.config.industrial, self.config.parkland],
            dtype=np.float64,
        )
        labels = ["residential", "commercial", "industrial", "parkland"]

        out: list[BlockSpec] = []
        for idx, block in enumerate(blocks):
            # Commercial clusters at the core; industrial pushes to the edge.
            w = base.copy()
            w[1] *= 1.0 + (1.0 - norm_r[idx]) * 1.8   # commercial
            w[2] *= 0.4 + norm_r[idx] * 1.4           # industrial
            w[3] *= 0.8 + norm_r[idx] * 0.6           # parkland
            w /= w.sum()
            zoning = str(self.rng.choice(labels, p=w))
            density = float(np.clip(1.0 - norm_r[idx], 0.05, 1.0) * self.config.density_gradient)
            out.append(
                BlockSpec(
                    block_id=block.block_id,
                    footprint=block.footprint,
                    zoning=zoning,
                    density=density,
                    height_m=float(self.rng.uniform(6, 90) * density),
                )
            )
        return out