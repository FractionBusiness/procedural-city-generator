"""Headless CLI entry — `citygen generate --preset coastal --seed 42`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

from citygen.core.pipeline import CityPipeline
from citygen.core.types import CitySpec
from citygen.services.config_loader import load_profile


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="citygen", description="AI procedural city generator")
    sub = p.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser("generate", help="generate a city from a profile")
    gen.add_argument("--profile", default="config/default.yaml")
    gen.add_argument("--preset", default=None, help="override preset name under config/presets/")
    gen.add_argument("--seed", type=int, default=None)
    gen.add_argument("--out", type=Path, default=None)
    gen.add_argument("--blocks", type=int, default=None, help="cap block count")

    sub.add_parser("doctor", help="verify runtime deps and model checkpoints")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.cmd == "doctor":
        from citygen.services.env_probe import run_doctor
        return run_doctor()

    profile = load_profile(args.profile, preset=args.preset)
    if args.seed is not None:
        profile.seed = args.seed
    if args.out is not None:
        profile.output_dir = args.out
    if args.blocks is not None:
        profile.grid.max_blocks = args.blocks

    spec = CitySpec.from_profile(profile)
    logger.info("generating city: seed={} blocks<={}", spec.seed, spec.grid.max_blocks)

    pipeline = CityPipeline(spec)
    result = pipeline.run()
    logger.success("wrote {} artifacts to {}", len(result.artifacts), result.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())