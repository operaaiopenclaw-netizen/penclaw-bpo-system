# Orkestra - Sistema de Gestão Financeira para Eventos
# v1.0 - Multi-Agent Orchestration System

__version__ = "1.0.0"
__author__ = "Orkestra Finance Brain"

from pathlib import Path

# Paths base
BASE_DIR = Path(__file__).parent
AGENTS_DIR = BASE_DIR / "agents"
ENGINE_DIR = BASE_DIR / "engine"
MEMORY_DIR = BASE_DIR / "memory"
SCHEMAS_DIR = BASE_DIR / "schemas"

__all__ = ['BASE_DIR', 'AGENTS_DIR', 'ENGINE_DIR', 'MEMORY_DIR', 'SCHEMAS_DIR']
