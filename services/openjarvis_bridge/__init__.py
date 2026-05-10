"""
OpenJarvis Bridge — local-first agent runtime for Powerhouse.

Integrates Stanford's OpenJarvis framework to provide on-device AI
alongside Powerhouse's cloud agent swarm. Simple queries run locally
(free, instant, private). Complex tasks escalate to the cloud.

Usage:
    from services.openjarvis_bridge import OpenJarvisBridge, HybridRouter

    bridge = OpenJarvisBridge()
    result = await bridge.ask("What's my margin on Sukienki XL?")
"""

from .bridge import OpenJarvisBridge, BridgeResult, ExecutionTarget
from .router import HybridRouter
from .config import BridgeConfig, DEFAULT_CONFIG

__all__ = [
    "OpenJarvisBridge",
    "BridgeResult",
    "ExecutionTarget",
    "HybridRouter",
    "BridgeConfig",
    "DEFAULT_CONFIG",
]
