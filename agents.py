"""
agents.py — Orquestador / Planeador del workshop de deteccion de fraude.

Uso:
    python agents.py <nombre_transaccion>

Ejemplos:
    python agents.py transactionA
    python agents.py transactionA.json

El archivo se busca en la carpeta data/ relativa a este script.

Responsabilidades:
  1. Leer y validar el archivo de transaccion indicado.
  2. Consultar al Agente de Memoria si memoria=true.
  3. Elevar el riesgo a Critico si hay historial sospechoso previo.
  4. Ejecutar el pipeline secuencial de agentes LLM.
  5. Persistir el resultado via el Agente de Memoria.

Para cambiar agentes o reglas de negocio: editar pipeline.py — no este archivo.
"""

import asyncio
import json
import os
import sys

from config import get_backend
from backends.base import NormalizedMessage
from pipeline import PIPELINE, memory_read, memory_write

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Read global memory switch from .env (default: enabled)
# To disable: set USE_MEMORY=false in .env
USE_MEMORY: bool = os.getenv("USE_MEMORY", "true").strip().lower() == "true"

# ─────────────────────────────────────────────
# Orchestrator / Planner  (Python if/else — no LLM)
# ─────────────────────────────────────────────

def resolve_transaction_path(arg: str) -> str:
    """Build the full path to the transaction file from a bare name or filename."""
    name = arg if arg.endswith(".json") else f"{arg}.json"
    return os.path.join(DATA_DIR, name)


def load_transaction(path: str) -> list[dict]:
    """Load transaction file. File-level errors abort; returns list of raw transaction dicts."""
    if not os.path.exists(path):
        print(f"[Orchestrator] ERROR: Transaction file not found: {path}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            print(f"[Orchestrator] ERROR: Invalid JSON format — {exc}")
            sys.exit(1)

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list) or len(data) == 0:
        print("[Orchestrator] ERROR: Transaction file must contain a JSON object or a non-empty array.")
        sys.exit(1)

    return data


def validate_transaction(tx: dict) -> set:
    """Returns the set of missing required fields. Empty set means valid."""
    required_fields = {"clientId", "amount", "location"}
    return required_fields - tx.keys()


SUSPICIOUS_KEYWORDS = {"Sospechoso", "Critico", "ALERTA", "REVISION"}


def _is_suspicious_history(last_result: str) -> bool:
    return any(kw in last_result for kw in SUSPICIOUS_KEYWORDS)


def build_context(transaction: dict) -> str:
    """
    Rule: if USE_MEMORY=true (set in .env) and the client has a previous suspicious
    result, elevate risk by prefixing the context with a CRITICAL RISK flag.
    """
    client_id: str = transaction["clientId"]
    amount: float = transaction["amount"]
    location: str = transaction["location"]

    base_context = (
        f"Transaction data:\n"
        f"  Client ID : {client_id}\n"
        f"  Amount    : ${amount:,.2f} USD\n"
        f"  Location  : {location}\n"
    )

    if USE_MEMORY:
        history = memory_read(client_id)
        print(f"[Memory Agent] Reading history for {client_id}: {history}")

        if history and _is_suspicious_history(history.get("last_result", "")):
            print("[Memory Agent] Previous suspicious record found → elevating risk to Critico.")
            return f"⚠️ CRITICAL RISK — Client has a prior suspicious record.\n\n{base_context}"
    else:
        print("[Memory Agent] Memory disabled (USE_MEMORY=false). Skipping history lookup.")

    return base_context


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

async def main():
    # Argument handling
    if len(sys.argv) < 2:
        print("[Orchestrator] Usage: python agents.py <transaction_name>")
        print("  Example: python agents.py transactionA")
        print(f"  Available files in data/: {', '.join(os.listdir(DATA_DIR))}")
        sys.exit(1)

    transaction_path = resolve_transaction_path(sys.argv[1])

    # Step 1 — Orchestrator: load file
    print(f"[Orchestrator] Memory: {'ENABLED' if USE_MEMORY else 'DISABLED'} (USE_MEMORY in .env)")
    print(f"[Orchestrator] Loading {os.path.basename(transaction_path)}...")
    transactions = load_transaction(transaction_path)
    total = len(transactions)
    print(f"[Orchestrator] {total} transaction(s) loaded.")

    summary: list[dict] = []

    async with get_backend() as backend:
        agents = [await backend.create_agent(spec) for spec in PIPELINE]

        for idx, transaction in enumerate(transactions, start=1):
            print(f"\n{'=' * 60}")
            print(f"[Orchestrator] Transaction {idx}/{total}")

            # Step 2 — Validate individual transaction
            missing = validate_transaction(transaction)
            if missing:
                print(f"[Orchestrator] ERROR: Missing required fields: {missing} — skipping.")
                summary.append({
                    "idx": idx,
                    "clientId": transaction.get("clientId", "N/A"),
                    "amount": transaction.get("amount", 0),
                    "location": transaction.get("location", "N/A"),
                    "result": "SKIPPED — campos faltantes",
                })
                continue

            print(f"[Orchestrator] Client: {transaction['clientId']}")

            # Step 3 — Build enriched context (consults Memory Agent if needed)
            context = build_context(transaction)

            # Step 4 — Run the AI agent pipeline (declared in pipeline.py)
            outputs: list[list[NormalizedMessage]] = []
            async for event in backend.run_workflow(agents, context):
                if event.type == "output":
                    outputs.append(event.data)

            # Step 5 — Display results
            final_output = ""
            if outputs:
                print()
                for i, msg in enumerate(outputs[-1], start=1):
                    print(f"{'-' * 60}\n{i:02d} [{msg.author_name}]\n{msg.text}")
                final_output = outputs[-1][-1].text

            # Step 6 — Memory Agent: persist result
            if final_output:
                memory_write(transaction["clientId"], final_output)
                print(f"\n[Memory Agent] Result saved for client {transaction['clientId']}.")

            # Accumulate summary entry
            summary.append({
                "idx": idx,
                "clientId": transaction["clientId"],
                "amount": transaction["amount"],
                "location": transaction["location"],
                "result": final_output.splitlines()[0] if final_output else "Sin resultado",
            })

    # ─── Final Summary Table ───────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("RESUMEN DE TRANSACCIONES PROCESADAS")
    print(f"{'=' * 60}")
    header = f"{'#':>3}  {'Cliente':<10} {'Monto':>18}  {'Ubicación':<20} {'Resultado'}"
    print(header)
    print("-" * len(header))
    for entry in summary:
        amount_str = f"${entry['amount']:,.2f} USD"
        print(
            f"{entry['idx']:>3}  "
            f"{entry['clientId']:<10} "
            f"{amount_str:>18}  "
            f"{entry['location']:<20} "
            f"{entry['result']}"
        )
    print(f"{'=' * 60}")
    print(f"[Orchestrator] Done. Processed {total} transaction(s) from {os.path.basename(transaction_path)}.")


if __name__ == "__main__":
    asyncio.run(main())