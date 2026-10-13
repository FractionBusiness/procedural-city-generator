"""Typed domain objects for the generator. Pydantic v2 for the config-facing
types, frozen dataclasses for the hot-path geometry types."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


class GridConfig(BaseModel):
    block_size_m: int = 90
    road_width_m: int = 14
    sidewalk_width_m: int = 3
    max_blocks: int = 4096


class DiffusionConfig(BaseModel):
    checkpoint: str
    steps: int = 24
    guidance: float = 6.5
    tile_px: int = 512
    batch: int = 8
    device: str = "auto"


class RoadConfig(BaseModel):
    solver: str = "hybrid_astar"
    arterial_spacing_m: int = 620
    local_spacing_m: int = 140
    curvature_penalty: float = 0.35
    min_intersection_deg: int = 55


class ZoningConfig(BaseModel):
    residential: float = 0.52
    commercial: float = 0.21
    industrial: float = 0.14
    parkland: float = 0.13
    density_gradient: float = 0.7


class ExportConfig(BaseModel):
    formats: list[str] = Field(default_factory=lambda: ["obj", "gltf", "geojson"])
    bake_navmesh: bool = True
    lod_levels: int = 3


class Profile(BaseModel):
    name: str = "baseline-metropolis"
    seed: int = 20260117
    output_dir: Path = Path("./out")
    grid: GridConfig = Field(default_factory=GridConfig)
    diffusion: DiffusionConfig
    roads: RoadConfig = Field(default_factory=RoadConfig)
    zoning: ZoningConfig = Field(default_factory=ZoningConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)


@dataclass(frozen=True, slots=True)
class BlockSpec:
    """A single city block. Geometry lives in `footprint` (Nx2 float32, meters)."""
    block_id: int
    footprint: np.ndarray
    zoning: str
    density: float
    height_m: float


@dataclass(slots=True)
class RoadGraph:
    """Adjacency + edge geometry. `nodes` Nx2 float32, `edges` list of (i, j, polyline)."""
    nodes: np.ndarray
    edges: list[tuple[int, int, np.ndarray]] = field(default_factory=list)

    def add_edge(self, i: int, j: int, polyline: np.ndarray) -> None:
        self.edges.append((i, j, polyline))


@dataclass(slots=True)
class CitySpec:
    seed: int
    grid: GridConfig
    diffusion: DiffusionConfig
    roads: RoadConfig
    zoning: ZoningConfig
    export: ExportConfig
    output_dir: Path
    name: str = "baseline-metropolis"

    @classmethod
    def from_profile(cls, profile: Profile) -> "CitySpec":
        return cls(
            seed=profile.seed,
            grid=profile.grid,
            diffusion=profile.diffusion,
            roads=profile.roads,
            zoning=profile.zoning,
            export=profile.export,
            output_dir=profile.output_dir,
            name=profile.name,
        )


@dataclass(slots=True)
class GenerationResult:
    output_dir: Path
    artifacts: list[Path]
    stats: dict[str, Any] = field(default_factory=dict)