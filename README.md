# Deteccion de Transacciones Fraudulentas — Orquestacion de Agentes

Workshop de orquestacion de agentes de IA aplicado a un sistema de deteccion de fraude financiero.
Muestra como combinar un orquestador Python (logica de negocio determinista) con agentes LLM
y un agente de memoria persistente, sobre dos backends intercambiables.

> Nuevo en el workshop? Sigue la guia paso a paso en la carpeta [`workshop/`](workshop/).

## Clientes de prueba

| ID | Nombre | Perfil |
|---|---|---|
| C001 | Victor Medina | Historial de fraude confirmado |
| C002 | Ana Garcia | Cliente legitima habitual |
| C003 | Roberto Sanz | Empresario, montos altos legitimos |
| C004 | Laura Torres | Cliente nueva, sin historial |
| C005 | Carlos Mendez | Viajero frecuente, ubicaciones inusuales |

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
    transactionA.json    — 5 transacciones mezcladas (Dia 1): 2 pares de escalacion intra-lote
    transactionB.json    — 5 transacciones mezcladas (Dia 2): distintos patrones de riesgo
    transactionC.json    — 5 transacciones mezcladas (Fin de semana): enfasis geo-riesgo
    transactionD.json    — 5 transacciones mezcladas (Lunes corporativo): montos extremos
    transactionE.json    — 3 transacciones invalidas + 2 validas (validacion del Orquestador)
  backends/
    base.py              — Contrato comun para cualquier backend
    azure_backend.py     — Implementacion Azure AI Foundry
    github_backend.py    — Implementacion GitHub Models
```

> Para agregar un agente: crear `nuevo_agent.py`, importarlo en `pipeline.py` y aniadirlo a `PIPELINE`.
> `agents.py` no debe cambiar al modificar la logica de negocio.

## Requisitos

```sh
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

Activa el entorno virtual y ejecuta:

```sh
python agents.py <nombre_transaccion>
```

El nombre puede incluir o no la extension `.json`:

```sh
python agents.py transactionA
python agents.py transactionA.json  # equivalente
```

## Escenarios del workshop

> Ver la guia detallada con puntos de discusion en [workshop/03-PruebasBasicas.md](workshop/03-PruebasBasicas.md).

Cada archivo contiene un **array JSON de 5 transacciones** con los clientes mezclados. El Orquestador procesa cada transaccion en secuencia dentro del mismo run.

### Escenario 1 — Lote completo sin memoria

```sh
# Windows (PowerShell)
Remove-Item memory_store.json -ErrorAction SilentlyContinue

# Mac / Linux
rm -f memory_store.json
```

```sh
python agents.py transactionA
```

Resultado: 5 transacciones evaluadas de forma aislada. Resultados representativos:
- C001 $15,000 Desconocido → `🚨 ALERTA` (doble riesgo)
- C001 $500 Barcelona → `✅ APROBADA` (sin flags, sin historial)
- C005 $3,000 Lista Negra → `⚠️ REVISION` (blacklist)

---

### Escenario 2 — Mismo lote con memoria (escalacion intra-lote)

```sh
# Limpiar historial primero
Remove-Item memory_store.json -ErrorAction SilentlyContinue
```

```sh
python agents.py transactionA
```

Con `USE_MEMORY=true`, el resultado cambia para 2 transacciones gracias a la escalacion:

| Transaccion | Sin memoria | Con memoria | Razon |
|---|---|---|---|
| C001 $500 Barcelona (tx#4) | ✅ APROBADA | 🚨 ALERTA | Historial de tx#2 |
| C005 $1,200 Desconocido (tx#5) | ⚠️ REVISION | 🚨 ALERTA | Historial de tx#3 |

---

### Escenario 3 — Validacion: lote con errores y transacciones validas

```sh
python agents.py transactionE
```

`transactionE`: 3 transacciones invalidas (campos faltantes) + 2 validas al final. El Orquestador reporta cada error y continua el lote sin interrumpirlo. Las 2 transacciones validas se procesan normalmente.

---

### Reset entre escenarios

```sh
# Windows (PowerShell)
Remove-Item memory_store.json -ErrorAction SilentlyContinue

# Mac / Linux
rm -f memory_store.json
```

## Troubleshooting

- `Missing required environment variables`: revisar `.env` segun el backend elegido.
- `ModuleNotFoundError: truststore`: asegúrate de que el entorno virtual esté activo (`source labenv/bin/activate` en Mac/Linux o `labenv\Scripts\Activate.ps1` en Windows).
- Error de red a Azure: validar conectividad y endpoint de Foundry.
- Error de autenticacion GitHub: validar `GITHUB_TOKEN` y permisos del token.
- `Unknown model`: usar formato `openai/gpt-4o-mini` en `GITHUB_MODEL`.
