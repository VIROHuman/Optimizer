"""
Codal Engine Module.

This module contains the codal rule engines that enforce safety and compliance.
Each engine implements code-specific checks for transmission tower designs.

CRITICAL PRINCIPLES:
- Determines feasibility (PASS / FAIL)
- Enforces safety and compliance
- NEVER optimizes
- NEVER considers cost
"""

from codal_engine.base import CodalEngine
from codal_engine.is_engine import ISEngine
from codal_engine.iec_engine import IECEngine
from codal_engine.eurocode_engine import EurocodeEngine
from codal_engine.asce_engine import ASCEEngine

__all__ = [
    'CodalEngine',
    'ISEngine',
    'IECEngine',
    'EurocodeEngine',
    'ASCEEngine',
]

