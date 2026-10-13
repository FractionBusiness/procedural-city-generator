"""Staged synthesis pipeline: road graph → block partition → diffusion fill → zoning → export.

Stage order is fixed. Each stage is pure-ish (reads spec, returns new objects)
so the whole run is reproducible from `spec.seed` alone.
"""
from __future__ import annotations

import time
from pathlib import Path

from loguru import logger

from citygen.core.types import CitySpec, GenerationResult, RoadGraph
from citygen.handlers.road_handler import RoadHandler
from citygen.handlers.block_handler import BlockHandler
from citygen.handlers.zoning_handler import ZoningHandler
from citygen.services.diffusion_service import DiffusionService
from citygen.services.export_service import ExportService
from citygen.utils.rng import seeded_rng


class CityPipeline:
    """Orchestrates a full generation run. Not thread-safe; one instance per run."""

    def __init__(self, spec: CitySpec) -> None:
        self.spec = spec
        self.rng = seeded_rng(spec.seed)

    def run(self) -> GenerationResult:
        t0 = time.perf_counter()
        out = Path(self.spec.output_dir)
        out.mkdir(parents=True, exist_ok=True)

        logger.info("[1/5] solving road graph")
        graph: RoadGraph = RoadHandler(self.spec, self.rng).solve()

        logger.info("[2/5] partitioning blocks")
        blocks = BlockHandler(self.spec, self.rng).partition(graph)
        logger.debug("partitioned {} blocks", len(blocks))

        logger.info("[3/5] diffusion block fill ({} tiles)", len(blocks))
        diffuser = DiffusionService(self.spec.diffusion)
        blocks = diffuser.fill(blocks)

        logger.info("[4/5] zoning assignment")
        blocks = ZoningHandler(self.spec.zoning, self.rng).assign(blocks)

        logger.info("[5/5] export")
        exporter = ExportService(self.spec.export, out)
        artifacts = exporter.write(graph, blocks)

        elapsed = time.perf_counter() - t0
        stats = {
            "blocks": len(blocks),
            "road_edges": len(graph.edges),
            "elapsed_s": round(elapsed, 3),
        }
        logger.success("pipeline done in {:.2f}s — {} blocks", elapsed, len(blocks))
        return GenerationResult(output_dir=out, artifacts=artifacts, stats=stats)