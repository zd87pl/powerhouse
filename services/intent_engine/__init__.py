"""Phase 3: Declarative Intent Engine (.powerhouse.yml reconciler).

Watches for intent files and reconciles declared infrastructure state
with actual state — like a lightweight Kubernetes controller for your stack.
"""

from .engine import IntentEngine
from .schema import IntentFile, load_intent

__all__ = ["IntentEngine", "IntentFile", "load_intent"]
