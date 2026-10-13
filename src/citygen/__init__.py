"""procedural-city-generator — AI-driven city synthesis toolkit.

Public surface kept intentionally small; feature modules live under
subpackages (`handlers`, `services`, `models`, `utils`).
"""

from citygen.core.pipeline import CityPipeline
from citygen.core.types import CitySpec, BlockSpec, RoadGraph

__version__ = "0.9.3"
__all__ = ["CityPipeline", "CitySpec", "BlockSpec", "RoadGraph", "__version__"]