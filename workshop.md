# Workshop: Orquestación de Agentes de IA — Detección de Fraude

## ¿Qué vamos a construir?

Un sistema de detección de transacciones fraudulentas que combina:

- Un **Orquestador Python** — decide el flujo con `if/else`, sin IA
- Dos **agentes LLM** — analizan y generan reportes en lenguaje natural
- Un **agente de Memoria** — persiste historial entre ejecuciones

El patrón central del workshop es **orquestación secuencial con memoria**:

```
transaction.json
      │
      ▼
  Orquestador       ← valida, decide, enriquece el contexto
      │
      ▼
  Analizador (LLM)  ← detecta flags de riesgo
      │
      ▼
  Reporte (LLM)     ← genera decisión en lenguaje humano
      │
      ▼
  Memoria (Python)  ← guarda el resultado del cliente
```

### Conceptos clave que demostraremos

| Concepto | Dónde se ve |
|---|---|
| Orquestación secuencial | `pipeline.py` → `PIPELINE` list |
| Agente determinista vs LLM | `agents.py` (Python) vs `analyzer_agent.py` (LLM) |
| Memoria persistente entre sesiones | `memory_agent.py` + `memory_store.json` |
| Configuración global del comportamiento | `USE_MEMORY` en `.env` |
| Validación de inputs | `load_transaction()` en `agents.py` |

---

## Paso 1 — Verificar cuenta GitHub

1. Ir a [github.com](https://github.com) e iniciar sesión.
2. Confirmar que tienes acceso a **GitHub Models**:
   - Ir a [github.com/marketplace/models](https://github.com/marketplace/models)
   - Debe mostrar modelos disponibles (GPT-4o, Llama, etc.)
   - Si no aparece, verifica que tu cuenta esté activa y no sea nueva

---

## Paso 2 — Crear el Personal Access Token

1. Ir a **GitHub → Settings** (menú de usuario, esquina superior derecha)
2. En el menú lateral: **Developer settings**
3. Seleccionar **Personal access tokens → Fine-grained tokens**
4. Click en **Generate new token**
5. Configurar:
   - **Token name**: `workshop-agents`
   - **Expiration**: 7 days (suficiente para el workshop)
   - **Repository access**: `Public Repositories (read-only)`
   - **Permissions**: no se requieren permisos adicionales para GitHub Models
6. Click en **Generate token**
7. **Copiar el token inmediatamente** — no se muestra de nuevo

---

## Paso 3 — Configurar el archivo `.env`

Abrir el archivo `.env` en la carpeta `Python/`:

```ini
AGENT_BACKEND="github"

# Enable or disable memory across all scenarios (true/false)
USE_MEMORY=true

GITHUB_TOKEN="<pegar tu token aquí>"
GITHUB_MODEL="openai/gpt-4o-mini"
GITHUB_ENDPOINT="https://models.github.ai/inference"
```

**Variables importantes:**

| Variable | Descripción |
|---|---|
| `AGENT_BACKEND` | Backend a usar: `github` o `azure` |
| `USE_MEMORY` | `true` = activa el agente de memoria globalmente |
| `GITHUB_TOKEN` | Token generado en el Paso 2 |
| `GITHUB_MODEL` | Modelo a usar (formato: `openai/gpt-4o-mini`) |

---

## Paso 4 — Instalar dependencias y verificar entorno

Desde la carpeta `Python/`:

```powershell
labenv\Scripts\python.exe -m pip install -r requirements.txt
```

Verificar que el entorno responde:

```powershell
labenv\Scripts\python.exe agents.py
```

Debe mostrar:
```
[Orchestrator] Usage: python agents.py <transaction_name>
  Example: python agents.py transactionA
  Available files in data/: transactionA.json, ...
```

---

## Transacciones de ejemplo

Los archivos en `data/` cubren todos los escenarios del workshop:

| Archivo | Cliente | Monto | Ubicación | Propósito |
|---|---|---|---|---|
| `transactionA` | C001 | $15,000 | Desconocido | Dos flags de riesgo → Crítico |
| `transactionB` | C002 | $800 | Madrid | Sin flags → Normal |
| `transactionC` | C001 | $500 | Barcelona | Normal, pero C001 tiene historial |
| `transactionD` | C003 | $12,000 | Madrid | Un flag (monto) → Sospechoso |
| `transactionE` | C003 | *(incompleto)* | — | Validación del Orquestador |

---

## Escenario 1 — Sin memoria (`USE_MEMORY=false`)

**Objetivo:** mostrar que sin memoria, cada transacción se evalúa de forma aislada.

**1.1** En `.env`, cambiar:
```ini
USE_MEMORY=false
```

**1.2** Limpiar historial previo:
```powershell
Remove-Item memory_store.json -ErrorAction SilentlyContinue
```

**1.3** Ejecutar la transacción de alto riesgo:
```powershell
labenv\Scripts\python.exe agents.py transactionA
```
Resultado esperado: `🚨 ALERTA DE BLOQUEO INMEDIATO` (por monto + ubicación)

**1.4** Ejecutar la misma transacción C001 con valores normales:
```powershell
labenv\Scripts\python.exe agents.py transactionC
```
Resultado esperado: `✅ TRANSACCION APROBADA`

> **Punto de discusión:** Aunque C001 acaba de tener una transacción bloqueada,
> el sistema la aprueba sin memoria. ¿Es esto seguro?

**1.5** Probar el caso intermedio (un solo flag):
```powershell
labenv\Scripts\python.exe agents.py transactionD
```
Resultado esperado: `⚠️ TRANSACCION EN REVISION` (solo monto elevado, ubicación normal)

---

## Escenario 2 — Con memoria (`USE_MEMORY=true`)

**Objetivo:** mostrar cómo el historial del cliente influye en decisiones futuras.

**2.1** En `.env`, cambiar:
```ini
USE_MEMORY=true
```

**2.2** Limpiar historial para empezar desde cero:
```powershell
Remove-Item memory_store.json -ErrorAction SilentlyContinue
```

**2.3** Primera transacción de C001 — alto riesgo:
```powershell
labenv\Scripts\python.exe agents.py transactionA
```
Resultado esperado: `🚨 ALERTA DE BLOQUEO INMEDIATO`

**2.4** Abrir `memory_store.json` y mostrar el historial guardado:
```json
{
  "C001": {
    "last_result": "🚨 ALERTA DE BLOQUEO INMEDIATO: ..."
  }
}
```

**2.5** Segunda transacción de C001 — valores normales, pero con historial:
```powershell
labenv\Scripts\python.exe agents.py transactionC
```
Resultado esperado: `🚨 ALERTA DE BLOQUEO INMEDIATO`

Observar en el output:
```
[Memory Agent] Previous suspicious record found → elevating risk to Critico.
```

> **Punto de discusión:** La transacción C es normal por sus propios méritos ($500, Barcelona).
> La memoria es la única razón del bloqueo. ¿Cuándo es útil este patrón?
> ¿Cuándo podría ser injusto?

**2.6** Ejecutar transactionB (C002, cliente sin historial):
```powershell
labenv\Scripts\python.exe agents.py transactionB
```
Resultado esperado: `✅ TRANSACCION APROBADA`
(C002 no tiene historial → se evalúa normalmente)

---

## Escenario 3 — Archivos con problemas

**Objetivo:** mostrar cómo el Orquestador valida entradas antes de llamar a los LLM.

**3.1** Archivo con campos faltantes:
```powershell
labenv\Scripts\python.exe agents.py transactionE
```
Resultado esperado:
```
[Orchestrator] ERROR: Missing required fields: {'memoria', 'amount', 'location'}
```
Notar que **los agentes LLM no se invocan** — el Orquestador rechaza la entrada.

**3.2** Archivo que no existe:
```powershell
labenv\Scripts\python.exe agents.py transactionZ
```
Resultado esperado:
```
[Orchestrator] ERROR: Transaction file not found: ...\data\transactionZ.json
```

**3.3** Sin argumento:
```powershell
labenv\Scripts\python.exe agents.py
```
Resultado esperado: instrucción de uso con lista de archivos disponibles.

> **Punto de discusión:** El Orquestador actúa como guardián (gate-keeper).
> ¿Qué otras validaciones añadirías en un sistema real?

---

## Cómo añadir un nuevo agente (ejercicio)

1. Crear `verificador_agent.py` en `Python/` con un nuevo `AgentSpec`
2. Importarlo en `pipeline.py` y añadirlo a `PIPELINE`
3. Ejecutar cualquier transacción y observar el nuevo paso en el output

```python
# verificador_agent.py
from backends.base import AgentSpec

VERIFICADOR_AGENT = AgentSpec(
    name="verificador",
    instructions="""
    You are a compliance officer. Review the fraud analysis and check
    if the decision complies with local banking regulations.
    Output: COMPLIANT or NON-COMPLIANT with a one-line reason.
    """,
)
```

```python
# pipeline.py — añadir:
from verificador_agent import VERIFICADOR_AGENT

PIPELINE = [
    ANALYZER_AGENT,
    VERIFICADOR_AGENT,  # ← nuevo agente insertado aquí
    REPORT_AGENT,
]
```

---

## Reset completo entre sesiones

```powershell
Remove-Item memory_store.json -ErrorAction SilentlyContinue
```
