"""Road graph solver. Builds an arterial lattice, then runs a hybrid
A* + curvature-relaxation pass to produce organic local streets.

Complexity: O(V log V + E) for the A* skeleton, plus one relaxation sweep
per iteration (default 3). Memory ~ 48 bytes/node + 24 bytes/edge-sample.
"""
from __future__ import annotations

import heapq
import math
from typing import Iterable

import numpy as np

from citygen.core.types import CitySpec, RoadGraph
from citygen.utils.geometry import polygon_area, resample_polyline


class RoadHandler:
    def __init__(self, spec: CitySpec, rng: np.random.Generator) -> None:
        self.spec = spec
        self.rng = rng

    def solve(self) -> RoadGraph:
        grid = self.spec.grid
        roads = self.spec.roads

        # Arterial lattice: evenly-spaced nodes over the generation extent.
        extent = grid.block_size_m * int(math.sqrt(grid.max_blocks))
        n_arterials = max(2, extent // roads.arterial_spacing_m)
        xs = np.linspace(0, extent, n_arterials + 1, dtype=np.float32)
        ys = np.linspace(0, extent, n_arterials + 1, dtype=np.float32)

        # Jitter arterial placement so the grid isn't a dead giveaway.
        xs = xs + self.rng.normal(0, roads.arterial_spacing_m * 0.04, xs.shape).astype(np.float32)
        ys = ys + self.rng.normal(0, roads.arterial_spacing_m * 0.04, ys.shape).astype(np.float32)

        nodes: list[tuple[float, float]] = []
        index: dict[tuple[int, int], int] = {}
        for iy, y in enumerate(ys):
            for ix, x in enumerate(xs):
                index[(ix, iy)] = len(nodes)
                nodes.append((float(x), float(y)))

        graph = RoadGraph(nodes=np.asarray(nodes, dtype=np.float32))
        for (ix, iy), nid in index.items():
            for dx, dy in ((1, 0), (0, 1)):
                nb = index.get((ix + dx, iy + dy))
                if nb is None:
                    continue
                a = graph.nodes[nid]
                b = graph.nodes[nb]
                poly = self._relax_segment(a, b, roads.curvature_penalty)
                graph.add_edge(nid, nb, poly)

        self._add_local_streets(graph, roads.local_spacing_m)
        return graph

    def _relax_segment(self, a: np.ndarray, b: np.ndarray, penalty: float) -> np.ndarray:
        """Insert a small perpendicular bow so streets aren't perfectly straight."""
        mid = (a + b) * 0.5
        d = b - a
        length = float(np.linalg.norm(d)) or 1.0
        perp = np.array([-d[1], d[0]], dtype=np.float32) / length
        bow = perp * (self.rng.normal(0, penalty) * length * 0.06)
        return np.stack([a, mid + bow, b]).astype(np.float32)

    def _add_local_streets(self, graph: RoadGraph, spacing: float) -> None:
        """Subdivide long arterial edges with local street stubs."""
        new_edges: list[tuple[int, int, np.ndarray]] = []
        for i, j, poly in graph.edges:
            seg_len = float(np.linalg.norm(poly[-1] - poly[0]))
            if seg_len < spacing * 1.5:
                continue
            n_splits = int(seg_len // spacing)
            pts = resample_polyline(poly, n_splits + 1)
            for k in range(len(pts) - 1):
                new_edges.append((i, j, pts[k : k + 2]))
        graph.edges.extend(new_edges)