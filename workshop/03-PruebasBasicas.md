# 03 — Pruebas básicas (sin memoria)

En este módulo vas a explorar la arquitectura técnica de la solución, entender cómo el Microsoft Agent Framework organiza los agentes y ejecutar pruebas para todos los escenarios posibles sin activar la memoria.

---

## Arquitectura de la solución

El sistema está compuesto por cuatro componentes con roles bien diferenciados. Ningún componente conoce los detalles internos de otro; se comunican solo a través de interfaces definidas.

```
data/transactionX.json
         │
         ▼
┌────────────────────────────────────────────────┐
│  Orquestador / Planeador   (agents.py)         │
│  Tipo: Python determinista — sin LLM           │
│  • Valida campos requeridos (clientId, amount, │
│    location) — aborta antes de llamar al LLM   │
│  • Lee historial del cliente (si USE_MEMORY)   │
│  • Enriquece el contexto con "CRITICAL RISK"   │
│    si el cliente tiene alertas previas         │
│  • Decide el orden de ejecución del pipeline   │
└──────────────────┬─────────────────────────────┘
                   │ contexto enriquecido (texto)
                   ▼
         ┌──────────────────┐
         │    Analizador    │  agents.py → pipeline.py → PIPELINE[0]
         │  (El Detective)  │  Tipo: Agente LLM (AgentSpec)
         │                  │  • Evalúa monto y ubicación
         │                  │  • Aplica las reglas de negocio
         │                  │  • Emite flags + nivel de riesgo
         └────────┬─────────┘
                  │ texto con flags y nivel de riesgo
                  ▼
         ┌──────────────────┐
         │  Generador de    │  PIPELINE[1]
         │    Reporte       │  Tipo: Agente LLM (AgentSpec)
         │ (El Comunicador) │  • Recibe la salida del Analizador
         │                  │  • Emite la decisión en lenguaje humano
         └────────┬─────────┘
                  │ decisión final (🚨 / ⚠️ / ✅)
                  ▼
         ┌──────────────────┐
         │  Agente Memoria  │  memory_agent.py (llamado directamente)
         │ (El Historiador) │  Tipo: Python puro — sin LLM
         │                  │  • Persiste el resultado en
         │                  │    memory_store.json
         └──────────────────┘
```

---

## El Microsoft Agent Framework

El **Microsoft Agent Framework** es el SDK oficial de Microsoft para construir sistemas multi-agente con modelos de lenguaje de gran escala (LLM). Provee abstracciones que permiten definir agentes, orquestar su ejecución y conectarlos con Azure AI Foundry sin escribir código de bajo nivel.

### Conceptos clave del SDK

| Concepto | Descripción | En este proyecto |
|---|---|---|
| `AgentSpec` | Objeto de datos que describe un agente: su nombre e instrucciones (el system prompt) | `ANALYZER_AGENT` y `REPORT_AGENT` en `analyzer_agent.py` y `report_agent.py` |
| `AzureAIAgentClient` | Cliente que se conecta a un proyecto de Azure AI Foundry y registra los agentes | Usado en `backends/azure_backend.py` |
| `SequentialBuilder` | Orquestador que encadena agentes en secuencia: la salida de uno es la entrada del siguiente | Usado en `backends/azure_backend.py` |
| `Message` | Envoltorio de mensaje tipado para pasar datos entre agentes en el SDK | Usado al invocar el workflow en `azure_backend.py` |

### El backend de GitHub Models

El backend de GitHub Models (`github_backend.py`) **no usa el Microsoft Agent Framework SDK**. En su lugar, implementa la misma secuencia manualmente:

```
for agente in PIPELINE:
    respuesta = llamar_a_openai_api(instrucciones=agente, contexto_previo)
    contexto_previo = respuesta   # encadenamiento
```

Esto produce exactamente el mismo resultado que `SequentialBuilder`, pero sin los beneficios de Foundry (trazabilidad, escalado, gestión de agentes). La abstracción `AgentBackend` en `backends/base.py` garantiza que `agents.py` no necesite saber cuál backend está activo.

---

## Descripción técnica de cada componente

### Orquestador — `agents.py`

Implementa el patrón **Planner**: decide qué hacer y en qué orden antes de llamar a cualquier agente LLM. Es código Python puro, sin llamadas a modelos.

Funciones clave:

| Función | Qué hace |
|---|---|
| `load_transaction(path)` | Carga el archivo JSON y retorna la lista de transacciones; aborta si el archivo no existe o el JSON es inválido |
| `validate_transaction(tx)` | Verifica que la transacción tenga `clientId`, `amount` y `location`; retorna el conjunto de campos faltantes (vacío = válida) |
| `build_context(transaction)` | Construye el string de contexto; si hay historial sospechoso, antepone `"⚠️ CRITICAL RISK"` |
| `_is_suspicious_history(result)` | Escanea el resultado previo buscando palabras clave: `Sospechoso`, `Critico`, `ALERTA`, `REVISION` |
| `main()` | Punto de entrada: carga el lote, itera cada transacción, valida, enriquece, ejecuta el pipeline, imprime y persiste el resultado de cada una |

### Agente Analizador — `analyzer_agent.py`

Es un `AgentSpec`: solo contiene un nombre y un system prompt. No tiene código Python propio. Toda la lógica vive en las instrucciones que se pasan al LLM. El LLM evalúa:

- Si `amount > 10000` → flag `Sospechoso por Monto`
- Si `location` es `"Desconocido"` o `"Lista Negra"` → flag `Riesgo Geográfico`
- Si el contexto contiene `"CRITICAL RISK"` → nivel de riesgo forzado a `Crítico`

Salida: texto estructurado con los flags detectados y el nivel de riesgo asignado.

### Agente Generador de Reporte — `report_agent.py`

Otro `AgentSpec`. Recibe la salida del Analizador y la convierte en una decisión legible por humanos:

| Nivel de riesgo recibido | Decisión emitida |
|---|---|
| `Crítico` | 🚨 **ALERTA DE BLOQUEO INMEDIATO** + justificación |
| `Sospechoso` | ⚠️ **TRANSACCION EN REVISION** + justificación |
| `Normal` | ✅ **TRANSACCION APROBADA** |

### Agente de Memoria — `memory_agent.py`

Python puro, sin LLM. Implementa dos funciones:

- `memory_read(client_id)` → devuelve `{"last_result": "..."}` o `None` si no hay historial.
- `memory_write(client_id, result)` → actualiza `memory_store.json` con el resultado de la ejecución actual.

---

## Conceptos de orquestación

### Agente determinista vs. agente LLM

| Característica | Agente determinista (Python) | Agente LLM (AgentSpec) |
|---|---|---|
| Comportamiento | Siempre igual para los mismos inputs | Puede variar en redacción, consistente en decisión |
| Velocidad | Instantáneo | Latencia de red + inferencia |
| Costo | Cero | RUs o tokens por llamada |
| Uso ideal | Validación, routing, persistencia | Razonamiento, lenguaje natural, flexibilidad |

En este sistema, el **Orquestador y la Memoria son deterministas**; el **Analizador y el Reporte son LLM**.

### El patrón Agent-as-Prompt

Los agentes Analizador y Reporte son "agentes" porque tienen un rol definido, pero técnicamente son solo un system prompt. Esta técnica se llama **agent-as-prompt**: se delega la lógica de evaluación al LLM a través de instrucciones precisas en lugar de escribir código para cada regla.

Ventaja clave: **cambiar una regla de negocio no requiere modificar código** — solo se actualiza el texto en `analyzer_agent.py`.

### Chaining de contexto (encadenamiento)

En un pipeline secuencial, cada agente recibe como entrada la **salida del agente anterior** más el **contexto original**. Esto permite que el Generador de Reporte pueda leer tanto los datos de la transacción como el análisis del Analizador para producir una decisión fundamentada.

---

## Pruebas básicas sin memoria

Asegúrate de que `.env` tenga:
```ini
USE_MEMORY=false
```

Activa el entorno virtual si no lo has hecho en esta sesión:

```sh
# Windows (PowerShell)
labenv\Scripts\Activate.ps1

# Mac / Linux
source labenv/bin/activate
```

Limpia cualquier historial previo antes de comenzar:

```sh
# Windows (PowerShell)
Remove-Item memory_store.json -ErrorAction SilentlyContinue

# Mac / Linux
rm -f memory_store.json
```

---

### Formato de los archivos de transacciones

Cada archivo en `data/` es un **array JSON** con múltiples transacciones. Al ejecutar `python agents.py transactionA`, el Orquestador carga las 5 transacciones del archivo y las procesa **de forma secuencial**: valida cada una individualmente, ejecuta el pipeline completo para cada transacción válida, y persiste el resultado en memoria antes de pasar a la siguiente.

```json
[
  { "clientId": "C002", "amount": 800,   "location": "Madrid"      },
  { "clientId": "C001", "amount": 15000, "location": "Desconocido" },
  ...
]
```

Si una transacción tiene campos faltantes, el Orquestador la describe como inválida y **continúa con la siguiente** — el lote no se interrumpe.

---

### Perfiles de clientes

| Cliente | Nombre | Perfil |
|---|---|---|
| C001 | Victor Medina | Historial de fraude confirmado |
| C002 | Ana García | Cliente legítima habitual |
| C003 | Roberto Sanz | Empresario, montos altos legítimos |
| C004 | Laura Torres | Cliente nueva, sin historial |
| C005 | Carlos Méndez | Viajero frecuente, ubicaciones inusuales |

---

### Prueba principal — Lote completo sin memoria

```sh
python agents.py transactionA
```

El Orquestador procesa 5 transacciones en secuencia. Con `USE_MEMORY=false`, cada una se evalúa de forma completamente aislada — ningún resultado anterior influye sobre las siguientes.

Resultados esperados para `transactionA` (sin memoria):

| # | Cliente | Monto | Ubicación | Flags activos | Resultado esperado |
|---|---|---|---|---|---|
| 1 | C002 | $800 | Madrid | Ninguno | ✅ TRANSACCION APROBADA |
| 2 | C001 | $15,000 | Desconocido | Monto + Geográfico | 🚨 ALERTA DE BLOQUEO INMEDIATO |
| 3 | C005 | $3,000 | Lista Negra | Geográfico (blacklist) | ⚠️ TRANSACCION EN REVISION |
| 4 | C001 | $500 | Barcelona | Ninguno | ✅ TRANSACCION APROBADA |
| 5 | C005 | $1,200 | Desconocido | Geográfico | ⚠️ TRANSACCION EN REVISION |

> **Observación clave:** La transacción #4 de C001 ($500, Barcelona) se aprueba sin problema. Con memoria activa, esto cambia drásticamente — lo verás en [04-PruebasConMemoria.md](04-PruebasConMemoria.md).

---

### Prueba de validación — Campos faltantes

```sh
python agents.py transactionE
```

`transactionE` contiene 3 transacciones con campos faltantes en distintas combinaciones, seguidas de 2 transacciones válidas. El Orquestador valida cada una individualmente, reporta el error y **continúa con la siguiente** sin llamar a ningún LLM.

Comportamiento esperado:
- Transacciones 1–3: mensaje de error con los campos faltantes, sin invocar el pipeline.
- Transacciones 4–5: procesadas normalmente (el lote no se interrumpe por los errores previos).

> Este es el patrón **fail-fast por transacción**: el Orquestador protege el sistema antes de gastar tokens o tiempo de inferencia, pero no aborta el lote completo por un subconjunto inválido.

---

### Prueba del archivo B — Día 2 de operaciones

```sh
python agents.py transactionB
```

`transactionB` incluye patrones distintos: C001 aparece con monto alto y blacklist (tx#3 → 🚨), C002 con transacciones normales (✅).

> Guarda esta observación para la sección de memoria: en transactionB, C001 vuelve a ser bloqueado. Si ya tenía historial de transactionA, ¿cambia algo el comportamiento?

---

## Resumen de escenarios cubiertos

| Escenario | Ejemplo | Resultado esperado |
|---|---|---|
| Doble riesgo (monto + geo) | C001, $15,000, Desconocido | 🚨 ALERTA DE BLOQUEO INMEDIATO |
| Un solo flag: monto alto | C003, $12,000, Madrid | ⚠️ TRANSACCION EN REVISION |
| Un solo flag: blacklist geográfico | C005, $3,000, Lista Negra | ⚠️ TRANSACCION EN REVISION |
| Un solo flag: ubicación desconocida | C004, $9,500, Desconocido | ⚠️ TRANSACCION EN REVISION |
| Cliente nuevo, sin flags | C004, $200, Valencia | ✅ TRANSACCION APROBADA |
| Valores normales, sin historial | C001, $500, Barcelona | ✅ TRANSACCION APROBADA |
| Validación: campos faltantes | `transactionE` tx#1–7 | ❌ Error (sin LLM) |
| Lote continúa tras errores | `transactionE` tx#8–10 | Procesadas normalmente |

---

## Punto de control

Al finalizar este módulo debes haber:

- [x] Entendido la arquitectura de cuatro componentes y el rol de cada uno.
- [x] Comprendido qué es el Microsoft Agent Framework y cómo se usa en este proyecto.
- [x] Diferenciado entre agentes deterministas y agentes LLM.
- [x] Ejecutado `transactionA` y verificado los 5 resultados esperados sin memoria.
- [x] Ejecutado `transactionE` y observado cómo el lote continúa tras errores de validación.

Continúa con [04-PruebasConMemoria.md](04-PruebasConMemoria.md) para activar la memoria y ver cómo el historial de un cliente cambia las decisiones del sistema — incluso dentro del mismo lote.
