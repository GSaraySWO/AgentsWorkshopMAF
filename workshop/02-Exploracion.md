# 02 — Exploración del escenario

En este módulo vas a entender el escenario de negocio del workshop, explorar el código con la ayuda de GitHub Copilot y hacer tu primera ejecución exitosa.

---

## El escenario de negocio

### Contexto

Eres parte del equipo de tecnología de un banco. El área de prevención de fraude necesita un sistema que procese transacciones financieras en tiempo real y decida automáticamente si deben **aprobarse**, **ponerse en revisión** o **bloquearse**.

Hasta ahora, este proceso era manual: un analista revisaba cada transacción y aplicaba criterios de riesgo a mano. El volumen creció y ya no es sostenible. El nuevo sistema debe:

- Evaluar cada transacción contra reglas de riesgo definidas por el negocio.
- Considerar el historial previo del cliente.
- Emitir una decisión clara y justificada en lenguaje natural.
- Ser trazable y auditable.

### Las reglas de negocio

El equipo de prevención de fraude definió las siguientes reglas:

| Regla | Condición | Consecuencia |
|---|---|---|
| **Monto elevado** | Monto de la transacción > $10,000 USD | Se marca como `Sospechoso por Monto` |
| **Riesgo geográfico** | Ubicación = `"Desconocido"` o `"Lista Negra"` | Se marca como `Riesgo Geográfico` |
| **Historial sospechoso** | El cliente tiene una alerta previa registrada | El riesgo se eleva automáticamente a `Crítico` |

### Decisiones posibles

Según los flags acumulados, el sistema emite una de estas tres decisiones:

| Nivel de riesgo | Decisión |
|---|---|
| Crítico (uno o más flags + historial, o dos flags simultáneos) | 🚨 **ALERTA DE BLOQUEO INMEDIATO** |
| Sospechoso (un flag, sin historial previo) | ⚠️ **TRANSACCION EN REVISION** |
| Normal (sin flags) | ✅ **TRANSACCION APROBADA** |

---

## Las transacciones del workshop

Los archivos en la carpeta `data/` representan transacciones reales de clientes ficticios. Cada una está diseñada para cubrir un escenario pedagógico específico:

| Archivo | Cliente | Monto | Ubicación | Escenario que representa |
|---|---|---|---|---|
| `transactionA.json` | C001 | $15,000 | Desconocido | **Dos flags activos** → riesgo máximo |
| `transactionB.json` | C002 | $800 | Madrid | **Sin flags**, cliente nuevo → caso normal |
| `transactionC.json` | C001 | $500 | Barcelona | **Sin flags por sí sola**, pero C001 tiene historial → el escenario clave de memoria |
| `transactionD.json` | C003 | $12,000 | Madrid | **Un solo flag** (monto elevado, ubicación segura) → caso intermedio |
| `transactionE.json` | C003 | *(sin monto ni ubicación)* | — | **Transacción incompleta** → prueba la validación del Orquestador |

Abre uno de los archivos para ver su estructura:

```sh
# Windows (PowerShell)
Get-Content data/transactionA.json

# Mac / Linux
cat data/transactionA.json
```

```json
{ "clientId": "C001", "amount": 15000, "location": "Desconocido" }
```

---

## Exploración del código con GitHub Copilot

Antes de ejecutar el código, vamos a entender cómo está estructurado usando GitHub Copilot como guía. Estos ejercicios usan el **panel de Chat** de Copilot (`Ctrl+Alt+I` o el ícono de chat en la barra lateral).

### Ejercicio 1 — Entender el punto de entrada

En el panel de chat de Copilot, selecciona el modo Ask y escribe:

```
¿Qué hace el archivo agents.py? ¿Cuál es su responsabilidad principal en el sistema?
```

Copilot debería explicar que `agents.py` es el **Orquestador**: valida la transacción de entrada, consulta el historial del cliente y decide el flujo antes de llamar a los agentes de IA.

> **Para reflexionar:** ¿Por qué tiene sentido separar la lógica de negocio (Python) de la lógica de lenguaje natural (LLM)?

---

### Ejercicio 2 — Entender cómo se enriquece el contexto

Abre el archivo `agents.py` en VS Code. Localiza la función `build_context` (aproximadamente en la línea 40).

**Selecciona todo el cuerpo de esa función** con el ratón. Luego, haz clic derecho → **Copilot → Explain**.

Copilot explicará que esta función:
1. Lee el historial del cliente desde `memory_store.json`.
2. Si el resultado anterior fue sospechoso, agrega el prefijo `"⚠️ CRITICAL RISK"` al mensaje que recibirá el agente Analizador.
3. Si no hay historial, envía la transacción tal cual.

> **Para reflexionar:** ¿Qué ventaja tiene hacerlo en Python (determinista) en lugar de pedirle al LLM que tome esa decisión?

---

### Ejercicio 3 — Entender la extensibilidad del pipeline

En el panel de chat de Copilot, en modo Ask, escribe:

```
¿Qué es la lista PIPELINE en pipeline.py y cómo se agregaría un nuevo agente al flujo?
```

Copilot mostrará que `PIPELINE` es una lista ordenada de `AgentSpec`. Para agregar un agente nuevo solo se necesita:
1. Crear un archivo con un nuevo `AgentSpec`.
2. Importarlo en `pipeline.py`.
3. Añadirlo a la lista `PIPELINE`.

`agents.py` no necesita modificarse.

---

### Ejercicio 4 — Comparar los dos backends

En el panel de chat de Copilot, escribe:

```
¿Qué diferencia hay entre backends/azure_backend.py y backends/github_backend.py? ¿Cómo logran el mismo resultado?
```

Copilot explicará que:
- `azure_backend.py` usa el **Microsoft Agent Framework SDK** (`SequentialBuilder`) para orquestar los agentes.
- `github_backend.py` implementa la misma secuencia manualmente con un bucle `for` sobre el `PIPELINE`, llamando a la API de GitHub Models directamente.
- Ambos producen el mismo resultado; son intercambiables a través de la variable `AGENT_BACKEND` en `.env`.

---

## Primera ejecución

Con el entorno configurado (`USE_MEMORY=false` en `.env`), vamos a hacer la primera ejecución con la transacción más sencilla: una transacción normal de un cliente nuevo.

### Paso 1 — Asegúrate de que la memoria está desactivada

Abre `.env` y confirma:

```ini
USE_MEMORY=false
```

### Paso 2 — Activa el entorno virtual (si no lo has hecho en esta sesión)

```sh
# Windows (PowerShell)
labenv\Scripts\Activate.ps1

# Mac / Linux
source labenv/bin/activate
```

### Paso 3 — Limpia cualquier historial previo

```sh
# Windows (PowerShell)
Remove-Item memory_store.json -ErrorAction SilentlyContinue

# Mac / Linux
rm -f memory_store.json
```

### Paso 4 — Ejecuta la transacción B

```sh
python agents.py transactionB
```

La transacción B es: **C002 | $800 | Madrid** — sin flags de riesgo, cliente sin historial.

Resultado esperado:

```
[Orchestrator] Loaded transaction: {'clientId': 'C002', 'amount': 800, 'location': 'Madrid'}
[Orchestrator] Memory disabled — skipping history lookup.
[analyzer] ...
[report] ...
✅ TRANSACCION APROBADA
```

> La salida exacta del texto puede variar entre ejecuciones porque es generada por el LLM, pero la decisión final (`✅ TRANSACCION APROBADA`) debe ser consistente.

---

## Resumen y punto de control

Al finalizar este módulo debes haber:

- [x] Entendido el escenario de negocio del banco y sus reglas de riesgo.
- [x] Identificado para qué sirve cada transacción de prueba.
- [x] Usado GitHub Copilot para explorar el Orquestador, el pipeline y los backends.
- [x] Ejecutado `transactionB` y obtenido `✅ TRANSACCION APROBADA` como primera ejecución exitosa.

Continúa con [03-PruebasBasicas.md](03-PruebasBasicas.md) para explorar la arquitectura técnica en detalle y probar todos los escenarios sin memoria.
