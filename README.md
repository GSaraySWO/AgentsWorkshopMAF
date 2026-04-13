# Deteccion de Transacciones Fraudulentas — Orquestacion de Agentes

Workshop de orquestacion de agentes de IA aplicado a un sistema de deteccion de fraude financiero.
Muestra como combinar un orquestador Python (logica de negocio determinista) con agentes LLM
y un agente de memoria persistente, sobre dos backends intercambiables.

> Nuevo en el workshop? Sigue la guia paso a paso en la carpeta [`workshop/`](workshop/).

## Guia del Workshop

Los modulos estan ordenados para completarse en secuencia. Cada uno incluye instrucciones,
puntos de discusion y comandos listos para ejecutar.

| # | Modulo | Descripcion |
|---|--------|-------------|
| 1 | [Requerimientos](workshop/01-Requerimientos.md) | Instala el software necesario y valida el entorno antes de empezar |
| 2 | [Exploracion del escenario](workshop/02-Exploracion.md) | Entiende el negocio, explora el codigo con Copilot y haz tu primera ejecucion |
| 3 | [Pruebas basicas (sin memoria)](workshop/03-PruebasBasicas.md) | Arquitectura tecnica y pruebas de todos los escenarios sin activar la memoria |
| 4 | [Pruebas con memoria](workshop/04-PruebasConMemoria.md) | Activa el Agente de Memoria y observa como el historial cambia las decisiones |
| 5 | [Siguientes pasos](workshop/05-SiguientesPasos.md) | Migra de GitHub Models a Azure AI Foundry con trazabilidad y escalado productivo |

## Arquitectura de agentes

```
data/transactionX.json
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Orquestador / Planeador  (agents.py — Python)      │
│  • Valida el archivo de entrada                     │
│  • Si USE_MEMORY=true, consulta al Agente Memoria   │
│  • Eleva riesgo a Critico si hay historial          │
│    sospechoso previo                                │
│  • Decide la secuencia de ejecucion                 │
└──────────────┬──────────────────────────────────────┘
               │ contexto enriquecido
               ▼
      ┌─────────────────┐
      │  Analizador     │  (LLM) Evalua monto y ubicacion
      │  (El Detective) │  segun reglas de negocio
      └────────┬────────┘
               │ flags + nivel de riesgo
               ▼
      ┌─────────────────┐
      │  Generador de   │  (LLM) Emite decision final
      │  Reporte        │  en lenguaje humano
      └────────┬────────┘
               │ resultado
               ▼
      ┌─────────────────┐
      │  Agente de      │  (Python) Persiste el resultado
      │  Memoria        │  en memory_store.json
      └─────────────────┘
```

### Descripcion de cada agente

| Agente | Tipo | Rol | Archivo |
|---|---|---|---|
| Orquestador | Python | Valida entrada, decide flujo, enriquece contexto con memoria | `agents.py` |
| Analizador | LLM | Evalua la transaccion con reglas de negocio hardcodeadas | `analyzer_agent.py` |
| Generador de Reporte | LLM | Formatea la decision final en lenguaje humano | `report_agent.py` |
| Agente de Memoria | Python | Lee y escribe historial de clientes en `memory_store.json` | `memory_agent.py` |

### Reglas de negocio del Analizador

- **Monto > $10,000 USD** → flag `Sospechoso por Monto`
- **Ubicacion = "Desconocido" o "Lista Negra"** → flag `Riesgo Geografico`

### Regla de memoria (Orquestador)

- Si `USE_MEMORY=true` (en `.env`) y el cliente tiene un resultado previo con flag de
  alerta o sospecha, el Orquestador eleva el riesgo a `Critico` antes de llamar a los
  agentes LLM, aunque la transaccion actual parezca normal.

### Salidas posibles del Reporte

| Riesgo | Salida |
|---|---|
| Critico | 🚨 ALERTA DE BLOQUEO INMEDIATO |
| Sospechoso | ⚠️ TRANSACCION EN REVISION |
| Normal | ✅ TRANSACCION APROBADA |

## Estructura de archivos

```
Python/
  agents.py              — Orquestador: valida, decide flujo, ejecuta pipeline
  pipeline.py            — Tabla de contenidos: imports + orden del pipeline
  analyzer_agent.py      — El Detective: reglas de deteccion de fraude
  report_agent.py        — El Comunicador: formato de la decision final
  memory_agent.py        — El Historiador: lectura y escritura de historial
  workshop.md            — Guia paso a paso del workshop
  memory_store.json      — Historial persistente de clientes (auto-creado)
  config.py              — Selector de backend por variable de entorno
  data/
    transactionA.json    — C001 | $15,000 | Desconocido  (alto riesgo, dos flags)
    transactionB.json    — C002 | $800    | Madrid       (normal, cliente nuevo)
    transactionC.json    — C001 | $500    | Barcelona    (normal, C001 tiene historial)
    transactionD.json    — C003 | $12,000 | Madrid       (un flag: monto elevado)
    transactionE.json    — C003 | campos faltantes       (validacion del Orquestador)
  backends/
    base.py              — Contrato comun para cualquier backend
    azure_backend.py     — Implementacion Azure AI Foundry
    github_backend.py    — Implementacion GitHub Models
```

> Para agregar un agente: crear `nuevo_agent.py`, importarlo en `pipeline.py` y aniadirlo a `PIPELINE`.
> `agents.py` no debe cambiar al modificar la logica de negocio.

## Requisitos

```powershell
pip install -r requirements.txt
```

## Configuracion

1. Copia `.env.example` a `.env`.
2. Define `AGENT_BACKEND` y `USE_MEMORY`:

> `USE_MEMORY=true` activa la memoria globalmente para todos los escenarios.
> Cambiar a `USE_MEMORY=false` para evaluar transacciones de forma aislada sin historial.

### Opcion 1: Azure AI Foundry

```ini
AGENT_BACKEND="azure"
USE_MEMORY=true
AZURE_AI_PROJECT_ENDPOINT="https://<your-project>.services.ai.azure.com/api/projects/<project-name>"
AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4.1"
```

### Opcion 2: GitHub Models

```ini
AGENT_BACKEND="github"
USE_MEMORY=true
GITHUB_TOKEN="<github-token>"
GITHUB_MODEL="openai/gpt-4o-mini"
GITHUB_ENDPOINT="https://models.github.ai/inference"
```

> `GITHUB_ENDPOINT` es opcional (por defecto `https://models.github.ai/inference`).

## Uso

```powershell
labenv\Scripts\python.exe agents.py <nombre_transaccion>
```

El nombre puede incluir o no la extension `.json`:

```powershell
labenv\Scripts\python.exe agents.py transactionA
labenv\Scripts\python.exe agents.py transactionA.json  # equivalente
```

## Escenarios del workshop

> Ver la guia detallada con puntos de discusion en [workshop/03-PruebasBasicas.md](workshop/03-PruebasBasicas.md).

### Escenario A — Alto riesgo (dos flags)

```powershell
Remove-Item memory_store.json -ErrorAction SilentlyContinue
labenv\Scripts\python.exe agents.py transactionA
```

`transactionA.json`: C001 | $15,000 | Desconocido

Resultado esperado: `🚨 ALERTA DE BLOQUEO INMEDIATO` (monto + ubicacion)

---

### Escenario B — Transaccion normal, cliente nuevo

```powershell
labenv\Scripts\python.exe agents.py transactionB
```

`transactionB.json`: C002 | $800 | Madrid

Resultado esperado: `✅ TRANSACCION APROBADA`

---

### Escenario C — Normal, pero cliente con historial sospechoso

Primero ejecutar el Escenario A para registrar C001. Luego:

```powershell
labenv\Scripts\python.exe agents.py transactionC
```

`transactionC.json`: C001 | $500 | Barcelona

Resultado con `USE_MEMORY=true`: `🚨 ALERTA DE BLOQUEO INMEDIATO` (escalada por memoria)
Resultado con `USE_MEMORY=false`: `✅ TRANSACCION APROBADA` (evaluada de forma aislada)

---

### Escenario D — Un solo flag: monto elevado, ubicacion normal

```powershell
labenv\Scripts\python.exe agents.py transactionD
```

`transactionD.json`: C003 | $12,000 | Madrid

Resultado esperado: `⚠️ TRANSACCION EN REVISION`

---

### Escenario E — Archivo con campos faltantes

```powershell
labenv\Scripts\python.exe agents.py transactionE
```

Resultado esperado: error claro del Orquestador, sin llamar a los LLM.

---

### Reset entre escenarios

```powershell
Remove-Item memory_store.json -ErrorAction SilentlyContinue
```

## Troubleshooting

- `Missing required environment variables`: revisar `.env` segun el backend elegido.
- `ModuleNotFoundError: truststore`: usar `labenv\Scripts\python.exe` en lugar de `python`.
- Error de red a Azure: validar conectividad y endpoint de Foundry.
- Error de autenticacion GitHub: validar `GITHUB_TOKEN` y permisos del token.
- `Unknown model`: usar formato `openai/gpt-4o-mini` en `GITHUB_MODEL`.
