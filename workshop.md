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

```sh
pip install -r requirements.txt
```

Verificar que el entorno responde:

```sh
python agents.py
```

Debe mostrar:
```
[Orchestrator] Usage: python agents.py <transaction_name>
  Example: python agents.py transactionA
  Available files in data/: transactionA.json, ...
```

---

## Transacciones de ejemplo

Cada archivo en `data/` es un **array JSON de 5 transacciones** con los clientes mezclados. El Orquestador las procesa de forma secuencial y actualiza la memoria despues de cada una.

| Archivo | Clientes | Propósito principal |
|---|---|---|
| `transactionA` | C001, C002, C005 | Dia 1: incluye 2 pares de escalacion con memoria |
| `transactionB` | C001–C005 | Dia 2: distintos montos y ubicaciones |
| `transactionC` | C001–C005 | Fin de semana: enfasis en geo-riesgo y blacklist |
| `transactionD` | C001–C005 | Lunes corporativo: montos extremos y doble riesgo |
| `transactionE` | C001, C003, C004 | 3 invalidas + 2 validas: validacion del Orquestador |

**Perfiles de los 5 clientes:**

| ID | Nombre | Perfil |
|---|---|---|
| C001 | Victor Medina | Historial de fraude confirmado |
| C002 | Ana García | Cliente legítima habitual |
| C003 | Roberto Sanz | Empresario, montos altos legítimos |
| C004 | Laura Torres | Cliente nueva, sin historial |
| C005 | Carlos Méndez | Viajero frecuente, ubicaciones inusuales |

---

## Escenario 1 — Sin memoria (`USE_MEMORY=false`)

**Objetivo:** mostrar que sin memoria, cada transacción se evalúa de forma aislada — incluso dentro del mismo lote.

**1.1** En `.env`, cambiar:
```ini
USE_MEMORY=false
```

**1.2** Limpiar historial previo:
```sh
# Windows (PowerShell)
Remove-Item memory_store.json -ErrorAction SilentlyContinue

# Mac / Linux
rm -f memory_store.json
```

**1.3** Ejecutar el lote completo:
```sh
python agents.py transactionA
```
Resultado: 5 transacciones procesadas en secuencia. Resultados representativos:
- tx#1 (C002, $800, Madrid) → `✅ TRANSACCION APROBADA`
- tx#2 (C001, $15,000, Desconocido) → `🚨 ALERTA DE BLOQUEO INMEDIATO` (monto + ubicación)
- tx#3 (C005, $3,000, Lista Negra) → `⚠️ TRANSACCION EN REVISION` (blacklist)
- tx#4 (C001, $500, Barcelona) → `✅ TRANSACCION APROBADA` (sin flags)

> **Punto de discusión:** C001 fue bloqueado en tx#2 y aprobado en tx#4 — dentro del mismo archivo. Sin memoria, el sistema no recuerda. ¿Es esto seguro?

**1.4** Probar el caso de validación:
```sh
python agents.py transactionE
```
Resultado esperado: 3 errores de validación (sin invocar LLM) + 2 transacciones válidas procesadas normalmente.

---

## Escenario 2 — Con memoria (`USE_MEMORY=true`)

**Objetivo:** mostrar cómo el historial del cliente influye en decisiones futuras — incluso dentro del mismo lote.

**2.1** En `.env`, cambiar:
```ini
USE_MEMORY=true
```

**2.2** Limpiar historial para empezar desde cero:
```sh
# Windows (PowerShell)
Remove-Item memory_store.json -ErrorAction SilentlyContinue

# Mac / Linux
rm -f memory_store.json
```

**2.3** Ejecutar el mismo lote que en el Escenario 1:
```sh
python agents.py transactionA
```

El Agente de Memoria guarda el resultado de cada transacción antes de pasar a la siguiente. Señalar los 2 pares de escalación:

| Par | Transacción 1 | Resultado | Transacción 2 | Resultado con memoria |
|---|---|---|---|---|
| C001 | tx#2 ($15,000, Desconocido) | 🚨 ALERTA | tx#4 ($500, Barcelona) | 🚨 ALERTA |
| C005 | tx#3 ($3,000, Lista Negra) | ⚠️ REVISION | tx#5 ($1,200, Desconocido) | 🚨 ALERTA |

**2.4** Después de la ejecución, mostrar el `memory_store.json`:
```sh
# Windows (PowerShell)
Get-Content memory_store.json

# Mac / Linux
cat memory_store.json
```

Debes ver entradas para 3 clientes.

> **Punto de discusión:** La transacción $500 en Barcelona (C001, tx#4)
es objetivamente normal. La memoria es la única razón del bloqueo. ¿Cuándo es útil este patrón?
> ¿Cuándo podría ser injusto?

**2.5** Observar en el output de las tx escaladas:
```
[Memory Agent] Previous suspicious record found → elevating risk to Critico.
```

---

## Escenario 3 — Lote con errores de validación

**Objetivo:** mostrar cómo el Orquestador valida cada transacción individualmente y continúa el lote aunque haya errores.

**3.1** Lote con campos faltantes en distintas combinaciones:
```sh
python agents.py transactionE
```
Resultado esperado:
- Transacciones 1–3: mensajes de error del Orquestador indicando qué campos faltan. **El LLM nunca se invoca** para estas.
- Transacción 4 (C001, $50,000, Lista Negra): doble riesgo extremo → `🚨 ALERTA DE BLOQUEO INMEDIATO`
- Transacción 5 (C004, $100, Madrid): procesada normalmente.

> **Punto clave:** El lote **no se interrumpe** por los errores de validación. El Orquestador actúa como guardián por transacción, no por lote.

**3.2** Archivo que no existe:
```sh
python agents.py transactionZ
```
Resultado esperado: error del Orquestador que sí aborta (el archivo no existe, no hay nada que procesar).

**3.3** Sin argumento:
```sh
python agents.py
```
Resultado esperado: instrucción de uso con lista de archivos disponibles.

> **Punto de discusión:** ¿Cuál es la diferencia entre un error a nivel de archivo (sys.exit) y un error a nivel de transacción (print + continue)? ¿Qué diseño es más adecuado para producción?

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

```sh
# Windows (PowerShell)
Remove-Item memory_store.json -ErrorAction SilentlyContinue

# Mac / Linux
rm -f memory_store.json
```
