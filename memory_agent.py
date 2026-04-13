"""
memory_agent.py — El Historiador

Responsabilidad: Persistir y recuperar el historial de transacciones por cliente.

Reglas de negocio:
  - Escritura: al finalizar cada proceso, guardar el resultado del cliente.
  - Lectura: si el cliente ya tiene un flag de alerta o sospecha previo,
    el Orquestador (agents.py) elevara el riesgo de la transaccion actual a Critico.

El archivo memory_store.json se crea automaticamente en el primer run.
"""

import json
import os

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory_store.json")


def memory_read(client_id: str) -> dict | None:
    """Return the stored record for client_id, or None if not found."""
    if not os.path.exists(MEMORY_FILE):
        return None
    with open(MEMORY_FILE, encoding="utf-8") as f:
        store = json.load(f)
    return store.get(client_id)


def memory_write(client_id: str, result: str) -> None:
    """Persist the latest result for client_id."""
    store: dict = {}
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, encoding="utf-8") as f:
            store = json.load(f)
    store[client_id] = {"last_result": result}
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
