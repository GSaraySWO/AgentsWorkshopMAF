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
| `load_transaction(path)` | Valida que el JSON existe y tiene los campos `clientId`, `amount`, `location` |
| `build_context(transaction)` | Construye el string de contexto; si hay historial sospechoso, antepone `"⚠️ CRITICAL RISK"` |
| `_is_suspicious_history(result)` | Escanea el resultado previo buscando palabras clave: `Sospechoso`, `Critico`, `ALERTA`, `REVISION` |
| `main()` | Punto de entrada: carga, enriquece, ejecuta el pipeline, imprime y persiste el resultado |

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

### Prueba 1 — Dos flags activos: bloqueo inmediato

**transactionA:** C001 | $15,000 | Desconocido

Ambas reglas se activan: monto elevado Y ubicación desconocida.

```sh
python agents.py transactionA
```

Resultado esperado: `🚨 ALERTA DE BLOQUEO INMEDIATO`

> El Analizador detecta dos flags (`Sospechoso por Monto` + `Riesgo Geográfico`) y asigna nivel `Crítico`. El Generador de Reporte emite el bloqueo.

---

### Prueba 2 — Sin flags: transacción aprobada

**transactionB:** C002 | $800 | Madrid

Ninguna regla se activa. Cliente nuevo sin historial.

```sh
python agents.py transactionB
```

Resultado esperado: `✅ TRANSACCION APROBADA`

---

### Prueba 3 — Un solo flag: en revisión

**transactionD:** C003 | $12,000 | Madrid

Solo se activa la regla de monto (> $10,000). La ubicación es segura.

```sh
python agents.py transactionD
```

Resultado esperado: `⚠️ TRANSACCION EN REVISION`

> Un solo flag produce nivel `Sospechoso`, no `Crítico`. El sistema no bloquea, sino que envía a revisión manual.

---

### Prueba 4 — Validación del Orquestador: transacción incompleta

**transactionE:** C003 | *(sin monto ni ubicación)*

Esta transacción está intencionalmente incompleta para probar la línea de defensa del Orquestador.

```sh
python agents.py transactionE
```

Resultado esperado: un mensaje de error del Orquestador indicando campos faltantes. **El LLM nunca se invoca.**

> Este es el patrón **fail-fast**: antes de gastar tokens o crear latencia, el Orquestador verifica que los datos sean válidos.

---

### Prueba 5 — Sin flags pero cliente con historial (sin memoria activa)

**transactionC:** C001 | $500 | Barcelona

Por sí sola, esta transacción no activa ninguna regla. Con `USE_MEMORY=false`, el historial de C001 se ignora.

```sh
python agents.py transactionC
```

Resultado esperado: `✅ TRANSACCION APROBADA`

> **Guarda este resultado**. En la sección [04-PruebasConMemoria.md](04-PruebasConMemoria.md) ejecutarás exactamente el mismo comando, pero con memoria activada, y el resultado será completamente diferente.

---

## Resumen de resultados esperados

| Transacción | Flags activos | Resultado esperado |
|---|---|---|
| A — C001, $15,000, Desconocido | Monto + Geográfico | 🚨 ALERTA DE BLOQUEO INMEDIATO |
| B — C002, $800, Madrid | Ninguno | ✅ TRANSACCION APROBADA |
| D — C003, $12,000, Madrid | Monto | ⚠️ TRANSACCION EN REVISION |
| E — C003, incompleta | N/A | ❌ Error de validación (sin LLM) |
| C — C001, $500, Barcelona | Ninguno | ✅ TRANSACCION APROBADA |

---

## Punto de control

Al finalizar este módulo debes haber:

- [x] Entendido la arquitectura de cuatro componentes y el rol de cada uno.
- [x] Comprendido qué es el Microsoft Agent Framework y cómo se usa en este proyecto.
- [x] Diferenciado entre agentes deterministas y agentes LLM.
- [x] Ejecutado las cinco pruebas y verificado los resultados esperados.

Continúa con [04-PruebasConMemoria.md](04-PruebasConMemoria.md) para activar la memoria y ver cómo el historial de un cliente cambia las decisiones del sistema.
