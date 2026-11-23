"""Agent-based escalator simulator: stand-on-both-sides vs stand-right-walk-left."""
from .config import SimConfig
from .engine import Simulation
from .experiments import compare, sweep
from .strategies import Strategy, available_strategies, register

__all__ = [
    "SimConfig", "Simulation", "Strategy", "available_strategies", "register",
    "compare", "sweep",
]
__version__ = "0.1.0"
