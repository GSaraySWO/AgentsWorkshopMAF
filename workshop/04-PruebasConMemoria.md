# 04 — Pruebas con memoria

En este módulo vas a activar el Agente de Memoria, entender cómo persiste el historial de clientes entre ejecuciones y observar cómo ese historial cambia las decisiones del sistema sobre transacciones que, vistas de forma aislada, parecerían normales.

---

## ¿Por qué necesitan memoria los agentes?

Los sistemas de agentes sin memoria tratan cada ejecución como si fuera la primera. En el contexto de detección de fraude, esto es un problema:

- Un cliente fraudulento puede hacer una transferencia grande (bloqueada), luego intentar una pequeña (aprobada sin contexto).
- Un sistema sin memoria aprobaría la segunda transacción aunque el mismo cliente fuera bloqueado segundos antes.

La **memoria persistente** permite que el Orquestador sepa que C001 ya fue marcado como sospechoso y eleve automáticamente el nivel de riesgo de sus transacciones futuras, **independientemente de los valores actuales de la transacción**.

---

## Tipos de memoria en sistemas de agentes

| Tipo | Dónde vive | Duración | Ejemplo en este proyecto |
|---|---|---|---|
| **En memoria (in-process)** | RAM, variables Python | Solo durante la ejecución actual | El contexto que pasa entre Analizador y Reporte |
| **Persistente (externa)** | Archivo, base de datos | Entre sesiones y reinicios | `memory_store.json` — historial de clientes |
| **Semántica / vectorial** | Vector store | Entre sesiones, con búsqueda por similitud | (Próxima evolución con Azure Cosmos DB) |

En este workshop usamos **memoria persistente simple**: un archivo JSON que actúa como base de datos de historial de clientes.

---

## Cómo funciona `memory_store.json`

El archivo se crea automáticamente en la primera escritura y se actualiza en cada ejecución. Su estructura es:

```json
{
  "C001": {
    "last_result": "🚨 ALERTA DE BLOQUEO INMEDIATO: Transacción bloqueada..."
  },
  "C002": {
    "last_result": "✅ TRANSACCION APROBADA"
  }
}
```

- La **clave** es el `clientId` de la transacción.
- El **valor** es el texto completo de la última decisión del Generador de Reporte para ese cliente.
- Cada nueva ejecución para ese cliente **sobrescribe** el resultado anterior.

---

## El flujo técnico completo con memoria

El Orquestador en `agents.py` coordina la memoria en dos momentos:

### Al iniciar — lectura

```
load_transaction()
      │
      ▼
memory_read(clientId)           ← lee memory_store.json
      │
      ▼
_is_suspicious_history(result)  ← busca palabras clave:
                                   {"Sospechoso", "Critico", "ALERTA", "REVISION"}
      │
      ├─ Si hay historial sospechoso → antepone "⚠️ CRITICAL RISK" al contexto
      │                                El Analizador LLM interpretará esto como Crítico
      │
      └─ Si no hay historial → el contexto es la transacción tal cual
```

### Al terminar — escritura

```
resultado final del Reporte
      │
      ▼
memory_write(clientId, resultado)  ← actualiza memory_store.json
```

El Agente de Memoria no llama al LLM en ningún momento. Es código Python puro que opera sobre un archivo JSON.

---

## Activar la memoria

Abre `.env` y cambia:

```ini
USE_MEMORY=true
```

---

## Demo completa: escalación dentro de un mismo lote

Este es el "momento aha" del workshop: al procesar un lote de transacciones con memoria activa, el historial de un cliente se actualiza **después de cada transacción** — lo que significa que transacciones más tardías del mismo cliente en el mismo archivo pueden tener resultados completamente diferentes a las primeras.

### Paso 1 — Activar el entorno y limpiar el historial

Activa el entorno virtual si no lo has hecho en esta sesión:

```sh
# Windows (PowerShell)
labenv\Scripts\Activate.ps1

# Mac / Linux
source labenv/bin/activate
```

Empieza desde cero para que el resultado sea reproducible:

```sh
# Windows (PowerShell)
Remove-Item memory_store.json -ErrorAction SilentlyContinue

# Mac / Linux
rm -f memory_store.json
```

---

### Paso 2 — Correr el lote completo con memoria activa

```sh
python agents.py transactionA
```

Las 5 transacciones se procesan en orden. El Agente de Memoria escribe el resultado de cada transacción **antes** de pasar a la siguiente. Observa los 2 pares de escalación:

| # | Cliente | Monto | Ubicación | Sin memoria | Con memoria | Motivo |
|---|---|---|---|---|---|---|
| 1 | C002 | $800 | Madrid | ✅ | ✅ | Sin flags, sin historial |
| 2 | C001 | $15,000 | Desconocido | 🚨 | 🚨 | Doble riesgo → historial guardado |
| 3 | C005 | $3,000 | Lista Negra | ⚠️ | ⚠️ | Blacklist → historial guardado |
| 4 | C001 | $500 | Barcelona | ✅ | **🚨** | ← escalación: historial de tx#2 |
| 5 | C005 | $1,200 | Desconocido | ⚠️ | **🚨** | ← escalación: historial de tx#3 |

Los dos pares de escalación en una sola ejecución:
- **C001:** tx#2 (🚨 ALERTA) → tx#4 ($500 Barcelona → 🚨 ALERTA)
- **C005:** tx#3 (⚠️ REVISION) → tx#5 ($1,200 Desconocido → 🚨 ALERTA)

---

### Paso 3 — Inspeccionar el historial al final del lote

```sh
# Windows (PowerShell)
Get-Content memory_store.json

# Mac / Linux
cat memory_store.json
```

Debes ver entradas para 3 clientes. El valor de cada uno refleja la **última transacción procesada** del lote:

```json
{
  "C002": { "last_result": "✅ TRANSACCION APROBADA" },
  "C001": { "last_result": "🚨 ALERTA DE BLOQUEO INMEDIATO: ..." },
  "C005": { "last_result": "🚨 ALERTA DE BLOQUEO INMEDIATO: ..." }
}
```

> **Detalle técnico:** C002 termina con ✅ (tx#1, $800, Madrid). La memoria refleja siempre el resultado más reciente, no el “peor” histórico.

---

### Paso 4 — El mecanismo de escalación en detalle

Para entender por qué tx#4 (C001, $500, Barcelona) cambia de resultado:

```
[Memoria] Lectura de historial de C001...
  → last_result: "🚨 ALERTA DE BLOQUEO INMEDIATO: ..."
  → _is_suspicious_history() detecta "ALERTA" → True
  → Orquestador antepone "⚠️ CRITICAL RISK" al contexto

[Analizador recibe]:
  "⚠️ CRITICAL RISK — Client has a prior suspicious record.
   Transaction data:
     Client ID: C001
     Amount   : $500.00 USD
     Location : Barcelona"

  → El Analizador asigna riesgo Crítico (instrucción explícita en el prompt)

[Reporte emite]: 🚨 ALERTA DE BLOQUEO INMEDIATO
```

La transacción $500 en Barcelona es objetivamente normal — el único motivo del bloqueo es el historial.

---

### Paso 5 — Lote con errores de validación (transactionE)

`transactionE` mezcla 3 transacciones inválidas con 2 válidas. Ejecutar con memoria activa:

```sh
python agents.py transactionE
```

Comportamiento esperado:
- Transacciones 1–3: el Orquestador reporta los campos faltantes y **continúa** (sin llamar al LLM, sin escribir en memoria).
- Transacción 4 (C001, $50,000, Lista Negra): doble riesgo extremo → 🚨 (actualiza historial de C001).
- Transacción 5 (C004, $100, Madrid): procesada normalmente → ✅ ó 🚨 dependiendo del historial previo de C004.

> Los errores de validación no interrumpen el lote ni corrompen la memoria — solo se saltan las transacciones inválidas.

---

## Comparación visual: con y sin memoria (mismo archivo, mismo run)

| # | Cliente | Valores | `USE_MEMORY=false` | `USE_MEMORY=true` | Razón |
|---|---|---|---|---|---|
| 4 | C001 | $500, Barcelona | ✅ APROBADA | 🚨 ALERTA | tx#2 (🚨) guardado antes de tx#4 |
| 5 | C005 | $1,200, Desconocido | ⚠️ REVISION | 🚨 ALERTA | tx#3 (⚠️) guardado antes de tx#5 |

> **Para reflexionar:** Las dos transacciones escaladas son normales por sus propios méritos. La memoria es la única razón del bloqueo.
>
> Pista: busca la lista `SUSPICIOUS_KEYWORDS` en `agents.py` y verifica si `"REVISION"` está incluida. ¿Por qué hace que una ⚠️ REVISION también escale las siguientes transacciones del mismo cliente?

---

## Punto de control

Al finalizar este módulo debes haber:

- [x] Activado `USE_MEMORY=true` en `.env`.
- [x] Ejecutado `transactionA` y observado los 2 pares de escalación intra-lote.
- [x] Inspeccionado `memory_store.json` al finalizar el lote y verificado los 3 clientes.
- [x] Ejecutado `transactionE` y confirmado que los errores de validación no interrumpen el procesamiento de las transacciones válidas.
- [x] Comprendido el flujo técnico completo: `memory_read` → `_is_suspicious_history` → enriquecimiento del contexto → Analizador LLM → `memory_write`.

Continúa con [05-SiguientesPasos.md](05-SiguientesPasos.md) para llevar este sistema a Azure AI Foundry y habilitarle trazabilidad y escalabilidad de producción.
