"""
pipeline.py — Tabla de contenidos del workshop.

Este archivo ensambla el pipeline declarando que agentes participan y en que orden.

  Para agregar un agente  →  crear su archivo (ej. nuevo_agent.py),
                             importarlo aqui y añadirlo a PIPELINE.
  Para cambiar el orden   →  reordenar los items de PIPELINE.
  Para modificar un agente →  abrir su archivo directamente.
"""

from analyzer_agent import ANALYZER_AGENT  # El Detective
from report_agent import REPORT_AGENT      # El Comunicador
from memory_agent import memory_read, memory_write  # El Historiador

# ─────────────────────────────────────────────
# Pipeline order  ← agregar / reordenar aqui
# ─────────────────────────────────────────────

PIPELINE = [
    ANALYZER_AGENT,
    REPORT_AGENT,
]

__all__ = ["PIPELINE", "memory_read", "memory_write"]

