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

## Demo completa: el escenario clave

Este es el "momento aha" del workshop: la misma transacción produce resultados completamente distintos dependiendo del historial del cliente.

### Paso 1 — Activar el entorno y limpiar el historial

Activa el entorno virtual si no lo has hecho en esta sesión:

```powershell
labenv\Scripts\Activate.ps1
```

Empieza desde cero para que el resultado sea reproducible:

```powershell
Remove-Item memory_store.json -ErrorAction SilentlyContinue
```

---

### Paso 2 — Primera transacción de C001 (alto riesgo)

```powershell
python agents.py transactionA
```

**transactionA:** C001 | $15,000 | Desconocido

Resultado esperado: `🚨 ALERTA DE BLOQUEO INMEDIATO`

---

### Paso 3 — Inspeccionar el historial guardado

Después de la ejecución, abre `memory_store.json`:

```powershell
Get-Content memory_store.json
```

Debes ver algo como:

```json
{
  "C001": {
    "last_result": "🚨 ALERTA DE BLOQUEO INMEDIATO: La transacción ha sido bloqueada..."
  }
}
```

La palabra `ALERTA` está presente en el resultado. Cuando el Orquestador lea este historial en la próxima ejecución de C001, `_is_suspicious_history()` devolverá `True` y agregará `"⚠️ CRITICAL RISK"` al contexto del Analizador.

---

### Paso 4 — Segunda transacción de C001 (valores normales, pero con historial)

```powershell
python agents.py transactionC
```

**transactionC:** C001 | $500 | Barcelona

Sin memoria, esta transacción sería aprobada: $500 no supera el umbral de $10,000 y Barcelona no es una ubicación sospechosa. **Pero ahora C001 tiene historial.**

Resultado esperado: `🚨 ALERTA DE BLOQUEO INMEDIATO`

El Orquestador detectó la alerta previa de C001, elevó el riesgo a `Crítico` en el contexto, y el Analizador LLM la interpretó como tal — aunque los valores de la transacción sean normales.

---

## Comparación visual: con y sin memoria

| | `USE_MEMORY=false` | `USE_MEMORY=true` |
|---|---|---|
| **transactionC** (C001, $500, Barcelona) | ✅ TRANSACCION APROBADA | 🚨 ALERTA DE BLOQUEO INMEDIATO |
| ¿Por qué? | No hay contexto de historial; solo se evalúan los valores actuales | El historial de C001 (bloqueado en transactionA) eleva el riesgo a Crítico |

---

## Prueba adicional: cliente sin historial sospechoso

Ejecuta una transacción de un cliente que no haya sido bloqueado:

```powershell
python agents.py transactionB
```

**transactionB:** C002 | $800 | Madrid

Con `USE_MEMORY=true`, si C002 no tiene historial (o su historial es `✅ TRANSACCION APROBADA`), `_is_suspicious_history()` devuelve `False` y la transacción se evalúa normalmente.

Resultado esperado: `✅ TRANSACCION APROBADA`

> **Para reflexionar:** ¿Qué pasaría si ejecutas `transactionD` (C003, $12,000, Madrid → ⚠️ EN REVISION) y luego `transactionC` con C003? ¿El sistema bloquearía a C003 por tener historial de revisión?
>
> Pista: busca la lista `SUSPICIOUS_KEYWORDS` en `agents.py` y verifica si `"REVISION"` está incluida.

---

## Punto de control

Al finalizar este módulo debes haber:

- [x] Activado `USE_MEMORY=true` en `.env`.
- [x] Ejecutado `transactionA` y verificado que el historial de C001 se guardó en `memory_store.json`.
- [x] Ejecutado `transactionC` y observado que el mismo cliente es bloqueado a pesar de que sus valores actuales no activan ninguna regla.
- [x] Comprendido el flujo técnico completo: `memory_read` → `_is_suspicious_history` → enriquecimiento del contexto → Analizador LLM → `memory_write`.

Continúa con [05-SiguientesPasos.md](05-SiguientesPasos.md) para llevar este sistema a Azure AI Foundry y habilitarle trazabilidad y escalabilidad de producción.
