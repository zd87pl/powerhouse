"""
OpenJarvis Bridge configuration.

Settings for the local OpenJarvis runtime and hybrid routing behavior.
"""

import os
from dataclasses import dataclass, field


@dataclass
class BridgeConfig:
    """Configuration for the OpenJarvis bridge."""

    # Engine settings
    engine: str = "ollama"  # ollama, vllm, llama.cpp, cloud
    local_model: str = "qwen3:4b"  # Default local model

    # Routing thresholds
    local_max_complexity: str = "simple"  # "trivial", "simple", "moderate"
    local_max_query_length: int = 2000   # Characters
    cloud_fallback: bool = True           # Fall back to cloud if local fails

    # Performance
    local_timeout_seconds: int = 30
    cloud_timeout_seconds: int = 300

    # Cost control
    cloud_max_cost_per_query: float = 1.0  # USD

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        """Load configuration from environment variables."""
        return cls(
            engine=os.getenv("OPENJARVIS_ENGINE", "ollama"),
            local_model=os.getenv("OPENJARVIS_LOCAL_MODEL", "qwen3:4b"),
            local_max_complexity=os.getenv("OPENJARVIS_LOCAL_MAX_COMPLEXITY", "simple"),
            local_max_query_length=int(os.getenv("OPENJARVIS_LOCAL_MAX_LENGTH", "2000")),
            cloud_fallback=os.getenv("OPENJARVIS_CLOUD_FALLBACK", "true").lower() == "true",
            local_timeout_seconds=int(os.getenv("OPENJARVIS_LOCAL_TIMEOUT", "30")),
            cloud_timeout_seconds=int(os.getenv("OPENJARVIS_CLOUD_TIMEOUT", "300")),
            cloud_max_cost_per_query=float(os.getenv("OPENJARVIS_CLOUD_MAX_COST", "1.0")),
        )


# Default config
DEFAULT_CONFIG = BridgeConfig()
