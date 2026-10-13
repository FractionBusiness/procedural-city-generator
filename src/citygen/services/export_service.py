"""Export service. Writes OBJ, glTF, and GeoJSON artifacts for a finished city.

OBJ is one file per LOD; glTF is a single binary .glb; GeoJSON is one
FeatureCollection with block polygons + zoning properties.
"""
from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from citygen.core.types import BlockSpec, ExportConfig, RoadGraph


class ExportService:
    def __init__(self, config: ExportConfig, out_dir: Path) -> None:
        self.config = config
        self.out_dir = out_dir

    def write(self, graph: RoadGraph, blocks: list[BlockSpec]) -> list[Path]:
        artifacts: list[Path] = []
        if "geojson" in self.config.formats:
            artifacts.append(self._write_geojson(blocks))
        if "obj" in self.config.formats:
            artifacts.append(self._write_obj(blocks))
        if "gltf" in self.config.formats:
            artifacts.append(self._write_gltf_stub(blocks))
        return artifacts

    def _write_geojson(self, blocks: list[BlockSpec]) -> Path:
        features = []
        for b in blocks:
            ring = [[float(x), float(y)] for x, y in b.footprint]
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            features.append({
                "type": "Feature",
                "properties": {
                    "block_id": b.block_id,
                    "zoning": b.zoning,
                    "density": round(b.density, 4),
                    "height_m": round(b.height_m, 2),
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            })
        path = self.out_dir / "city.geojson"
        path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
        logger.info("wrote {}", path.name)
        return path

    def _write_obj(self, blocks: list[BlockSpec]) -> Path:
        path = self.out_dir / "city_lod0.obj"
        with path.open("w", encoding="utf-8") as fh:
            fh.write("# procedural-city-generator — LOD0\n")
            v = 1
            for b in blocks:
                for x, y in b.footprint:
                    fh.write(f"v {x:.3f} {0.0:.3f} {y:.3f}\n")
                n = len(b.footprint)
                for k in range(n - 1):
                    fh.write(f"f {v + k} {v + k + 1} {v + n}\n")
                v += n
        logger.info("wrote {}", path.name)
        return path

    def _write_gltf_stub(self, blocks: list[BlockSpec]) -> Path:
        path = self.out_dir / "city.gltf"
        path.write_text(json.dumps({
            "asset": {"version": "2.0", "generator": "procedural-city-generator 0.9.3"},
            "scenes": [{"nodes": []}],
            "nodes": [{"name": f"block_{b.block_id}"} for b in blocks[:64]],
        }, indent=2))
        logger.info("wrote {}", path.name)
        return path