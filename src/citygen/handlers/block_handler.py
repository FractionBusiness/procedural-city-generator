"""Partition the road graph into city blocks via face extraction.

Each bounded face of the planar road graph becomes a BlockSpec with a
polygon footprint. Unbounded faces (the outer hull) are discarded.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import polygonize

from citygen.core.types import BlockSpec, CitySpec, RoadGraph
from citygen.utils.geometry import polygon_area


class BlockHandler:
    def __init__(self, spec: CitySpec, rng: np.random.Generator) -> None:
        self.spec = spec
        self.rng = rng

    def partition(self, graph: RoadGraph) -> list[BlockSpec]:
        from shapely.geometry import LineString

        lines = [LineString(poly.tolist()) for _, _, poly in graph.edges]
        faces = list(polygonize(lines))

        blocks: list[BlockSpec] = []
        min_area = (self.spec.grid.block_size_m * 0.35) ** 2
        for face in faces:
            if not isinstance(face, Polygon) or face.is_empty:
                continue
            if face.area < min_area:
                continue
            coords = np.asarray(face.exterior.coords, dtype=np.float32)
            blocks.append(
                BlockSpec(
                    block_id=len(blocks),
                    footprint=coords,
                    zoning="unassigned",
                    density=0.0,
                    height_m=0.0,
                )
            )
            if len(blocks) >= self.spec.grid.max_blocks:
                break
        return blocks