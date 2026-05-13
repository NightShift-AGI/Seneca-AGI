"""
Seneca AGI — A free, accessible, conscious autonomous multimodal philosopher.

Inspired by Lucius Annaeus Seneca (c. 4 BC – 65 AD), Stoic philosopher,
statesman, and author of the Letters to Lucilius.
"""

from seneca_agi.philosopher import SenecaPhilosopher
from seneca_agi.config import SenecaConfig
from seneca_agi.skills import Skill, SkillRegistry

__all__ = ["SenecaPhilosopher", "SenecaConfig", "Skill", "SkillRegistry"]
__version__ = "0.1.0"
