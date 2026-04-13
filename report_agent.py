"""
report_agent.py — El Comunicador

Responsabilidad: Formatear los hallazgos del Analizador en lenguaje humano.

Reglas de negocio:
  - Riesgo Critico     → "ALERTA DE BLOQUEO INMEDIATO"
  - Riesgo Sospechoso  → "TRANSACCION EN REVISION"
  - Riesgo Normal      → "TRANSACCION APROBADA"

Para modificar el formato o el tono del reporte: editar las instrucciones de REPORT_AGENT.
"""

from backends.base import AgentSpec

REPORT_AGENT = AgentSpec(
    name="report",
    instructions="""
    You are a reporting agent. Based on the fraud analysis provided, generate a final decision.

    Rules:
      - If the overall risk is Critico     → output "🚨 ALERTA DE BLOQUEO INMEDIATO" followed by a brief explanation.
      - If the overall risk is Sospechoso  → output "⚠️ TRANSACCION EN REVISION" followed by a brief explanation.
      - If the overall risk is Normal      → output "✅ TRANSACCION APROBADA".

    Keep the output concise and human-readable.
    """,
)
