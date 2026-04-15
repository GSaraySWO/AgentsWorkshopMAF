# 05 — Siguientes pasos

En este módulo vas a llevar el sistema de GitHub Models a **Azure AI Foundry** — la plataforma de producción de Microsoft para agentes de IA. Aprenderás a crear los recursos necesarios, conectar el código, habilitar trazabilidad con OpenTelemetry y explorar alternativas de escalado para un entorno productivo real.

---

## ¿Por qué pasar a Azure AI Foundry?

El backend de GitHub Models es ideal para desarrollo y workshops: no requiere suscripción de Azure y usa un token de GitHub. Sin embargo, en producción necesitas:

| Necesidad | GitHub Models | Azure AI Foundry |
|---|---|---|
| Identidad y autorización empresarial | Token personal | Azure Active Directory / RBAC |
| Cuotas controladas | Límites de tasa compartidos | Cuotas dedicadas por recurso |
| Trazabilidad y observabilidad | No nativo | OpenTelemetry integrado |
| SLA y alta disponibilidad | No ofrecido | SLA de Azure |
| Gestión de agentes centralizada | No aplica | Registro de agentes en Foundry |
| Multi-región y failover | No | Disponible |

---

## Parte 1 — Crear los recursos en Azure AI Foundry

### Paso 1 — Iniciar sesión en el portal de Azure AI Foundry

1. Ve a [ai.azure.com](https://ai.azure.com) en tu navegador.
2. Inicia sesión con tu cuenta de Microsoft o cuenta organizacional de Azure.

---

### Paso 2 — Crear un Azure AI Hub

El Hub es el contenedor de nivel superior que agrupa proyectos, modelos y recursos de Foundry.

1. En el menú lateral, selecciona **Hubs** → **Nuevo hub**.
2. Completa los campos:

   | Campo | Valor recomendado |
   |---|---|
   | **Nombre del hub** | `workshop-agents-hub` |
   | **Suscripción** | Tu suscripción de Azure |
   | **Grupo de recursos** | Crea uno nuevo: `rg-workshop-agents` |
   | **Región** | `East US 2` o `Sweden Central` (mejor disponibilidad de modelos) |
   | **Cuenta de Azure AI Services** | Crear nueva (se crea automáticamente) |

3. Haz clic en **Revisar + crear** → **Crear**.
4. Espera a que el despliegue complete (aproximadamente 2 minutos).

---

### Paso 3 — Crear un proyecto dentro del Hub

1. Desde el Hub recién creado, haz clic en **Nuevo proyecto**.
2. Completa los campos:

   | Campo | Valor recomendado |
   |---|---|
   | **Nombre del proyecto** | `fraud-detection-agents` |
   | **Hub** | El hub que acabas de crear |

3. Haz clic en **Crear**.

---

### Paso 4 — Desplegar un modelo

El proyecto necesita un modelo de lenguaje para que los agentes puedan invocar inferencias.

1. Dentro de tu proyecto, ve a **Modelos y endpoints** → **Desplegar modelo**.
2. Selecciona **Desplegar modelo base**.
3. Busca y selecciona **`gpt-4o-mini`** (o `gpt-4.1` si está disponible en tu región).
4. Configura el despliegue:

   | Campo | Valor |
   |---|---|
   | **Nombre del despliegue** | `gpt-4o-mini` |
   | **Tipo de despliegue** | Estándar |
   | **Versión del modelo** | La más reciente disponible |

5. Haz clic en **Desplegar**.
6. Espera a que el estado cambie a **Activo**.

---

### Paso 5 — Obtener el endpoint del proyecto

1. En tu proyecto, ve a la sección **Overview** (Información general).
2. Copia el valor de **Azure AI Services endpoint**. Tiene el formato:

   ```
   https://<nombre-hub>.services.ai.azure.com/api/projects/<nombre-proyecto>
   ```

Guarda este valor — lo necesitarás en el siguiente paso.

---

### Paso 6 — Instalar Azure CLI y autenticarte

Si no tienes Azure CLI instalado:

1. Descárgalo desde [learn.microsoft.com/cli/azure/install-azure-cli-windows](https://learn.microsoft.com/cli/azure/install-azure-cli-windows).
2. Instala con las opciones por defecto y reinicia la terminal.

Verifica la instalación:

```powershell
az --version
```

Inicia sesión con tu cuenta de Azure:

```powershell
az login
```

Se abrirá una ventana de navegador para autenticarte. Una vez completado, verifica que la suscripción correcta esté activa:

```powershell
az account show
```

Busca el campo `"name"` — debe coincidir con la suscripción donde creaste el hub. Si no, cámbiala:

```powershell
az account set --subscription "<nombre-o-id-de-tu-suscripción>"
```

---

## Parte 2 — Conectar el código al backend de Azure

### Paso 7 — Actualizar el archivo `.env`

Abre `.env` y reemplaza la configuración del backend por:

```ini
AGENT_BACKEND="azure"

USE_MEMORY=true

AZURE_AI_PROJECT_ENDPOINT="https://<nombre-hub>.services.ai.azure.com/api/projects/<nombre-proyecto>"
AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4o-mini"
```

> `GITHUB_TOKEN`, `GITHUB_MODEL` y `GITHUB_ENDPOINT` pueden dejarse tal cual — el código solo los usa cuando `AGENT_BACKEND="github"`.

### Paso 8 — Ejecutar con backend Azure

```sh
# Windows (PowerShell)
labenv\Scripts\Activate.ps1

# Mac / Linux
source labenv/bin/activate
```

```sh
# Windows (PowerShell)
Remove-Item memory_store.json -ErrorAction SilentlyContinue

# Mac / Linux
rm -f memory_store.json
```

```sh
python agents.py transactionA
```

La primera ejecución puede tardar entre 10 y 30 segundos adicionales mientras Azure AI Foundry registra los agentes en el proyecto. Las ejecuciones siguientes serán más rápidas.

Resultado esperado: el mismo `🚨 ALERTA DE BLOQUEO INMEDIATO` que con GitHub Models, pero ahora procesado por `SequentialBuilder` del Microsoft Agent Framework SDK sobre recursos de Azure.

---

## Parte 3 — Habilitar trazabilidad

Azure AI Foundry incluye trazabilidad integrada con OpenTelemetry. El paquete `opentelemetry-semantic-conventions-ai` ya está en `requirements.txt`.

### Paso 9 — Activar trazabilidad en el proyecto de Foundry

1. En el portal de Azure AI Foundry, abre tu proyecto.
2. Ve a **Configuración del proyecto** (ícono de engranaje en el menú lateral).
3. Selecciona la pestaña **Trazabilidad** o **Observabilidad**.
4. Activa el interruptor **Habilitar trazabilidad**.
5. Foundry creará automáticamente un workspace de **Application Insights** vinculado al proyecto.
6. Copia la **Cadena de conexión** (Connection string) de Application Insights — tiene el formato:
   ```
   InstrumentationKey=<guid>;IngestionEndpoint=https://...
   ```

### Paso 10 — Agregar la variable de conexión al `.env`

```ini
APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=<guid>;IngestionEndpoint=https://..."
```

### Paso 11 — Ejecutar y revisar las trazas

Ejecuta varias transacciones:

```powershell
python agents.py transactionA
python agents.py transactionC
python agents.py transactionB
```

Para ver las trazas en Foundry:

1. En el portal de Azure AI Foundry, ve a **Trazas** o **Tracing** en el menú lateral.
2. Verás cada ejecución como una traza con:
   - El tiempo total del pipeline.
   - Los mensajes enviados a cada agente (input/output).
   - La latencia por agente.
   - El número de tokens consumidos.

Esta visibilidad es fundamental para debugging, optimización de costos y auditoría en entornos productivos.

---

## Parte 4 — Recomendaciones para escalar a producción

### Reemplazar `memory_store.json` con Azure Cosmos DB

El archivo JSON funciona en un entorno de un solo proceso, pero en producción:
- Múltiples instancias del proceso no pueden escribir simultáneamente sin riesgo de corrupción.
- El archivo no es accesible desde múltiples regiones.
- No escala a millones de clientes.

**Azure Cosmos DB** resuelve estos problemas y es la opción recomendada para sistemas de agentes de IA:

- **Partición por `clientId`**: alta cardinalidad, distribución uniforme, consultas O(1).
- **Consistencia garantizada**: sin condiciones de carrera al actualizar historial.
- **Escala global**: disponible en múltiples regiones con latencia < 10 ms.
- **Elastic scale**: paga solo por lo que usas.

Para migrar, reemplazarías `memory_agent.py` con cliente del SDK de Cosmos DB:

```python
# Instalar: pip install azure-cosmos
from azure.cosmos.aio import CosmosClient

async def memory_read(client_id: str) -> dict | None:
    async with CosmosClient(COSMOS_ENDPOINT, credential) as client:
        container = client.get_database_client(DB).get_container_client(CONTAINER)
        try:
            item = await container.read_item(item=client_id, partition_key=client_id)
            return {"last_result": item["last_result"]}
        except:
            return None
```

Consulta la guía completa: [Inicio rápido de Azure Cosmos DB para Python](https://learn.microsoft.com/azure/cosmos-db/nosql/quickstart-python).

---

### Gestionar secretos con Azure Key Vault

En producción, las credenciales no deben vivir en archivos `.env`. Usa **Azure Key Vault**:

1. Crea un Key Vault en el mismo grupo de recursos del Hub.
2. Agrega como secrets: `GITHUB-TOKEN`, `AZURE-AI-PROJECT-ENDPOINT`, etc.
3. Reemplaza `python-dotenv` con el SDK de Key Vault:

```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

client = SecretClient(vault_url=KEY_VAULT_URL, credential=DefaultAzureCredential())
github_token = client.get_secret("GITHUB-TOKEN").value
```

Guía: [Inicio rápido de Azure Key Vault para Python](https://learn.microsoft.com/azure/key-vault/secrets/quick-create-python).

---

### Containerizar con Docker y desplegar en Azure Container Apps

Para un despliegue independiente del entorno local:

**1. Crear un `Dockerfile`** en la carpeta `Python/`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "agents.py"]
```

**2. Construir y publicar la imagen:**

```powershell
az acr login --name <tu-acr>
docker build -t <tu-acr>.azurecr.io/fraud-agents:latest .
docker push <tu-acr>.azurecr.io/fraud-agents:latest
```

**3. Crear una Azure Container App:**

```powershell
az containerapp create `
  --name fraud-detection-agents `
  --resource-group rg-workshop-agents `
  --image <tu-acr>.azurecr.io/fraud-agents:latest `
  --env-vars AGENT_BACKEND=azure `
             AZURE_AI_PROJECT_ENDPOINT=<endpoint>
```

Azure Container Apps escala automáticamente a cero cuando no hay tráfico, lo que reduce los costos al mínimo.

Guía: [Inicio rápido de Azure Container Apps](https://learn.microsoft.com/azure/container-apps/quickstart-portal).

---

## Recursos adicionales

| Recurso | Enlace |
|---|---|
| Documentación de Azure AI Foundry | [learn.microsoft.com/azure/ai-foundry](https://learn.microsoft.com/azure/ai-foundry/) |
| Microsoft Agent Framework SDK | [github.com/azure/agent-framework](https://github.com/azure/agent-framework) |
| Azure Cosmos DB para sistemas de agentes IA | [learn.microsoft.com/azure/cosmos-db](https://learn.microsoft.com/azure/cosmos-db/) |
| OpenTelemetry para Python | [opentelemetry.io/docs/languages/python](https://opentelemetry.io/docs/languages/python/) |
| Azure Container Apps | [learn.microsoft.com/azure/container-apps](https://learn.microsoft.com/azure/container-apps/) |
| Azure Key Vault | [learn.microsoft.com/azure/key-vault](https://learn.microsoft.com/azure/key-vault/) |

---

## Felicitaciones

Has completado el workshop de orquestación de agentes de IA. A lo largo de los cinco módulos:

1. **Configuraste** el entorno completo con GitHub Models.
2. **Exploraste** el escenario de negocio y la arquitectura con GitHub Copilot.
3. **Probaste** todos los escenarios sin memoria y entendiste el Microsoft Agent Framework.
4. **Activaste** la memoria persistente y observaste su impacto en las decisiones.
5. **Conectaste** el sistema a Azure AI Foundry con el SDK nativo y habilitaste trazabilidad.

El sistema que construiste es la base de un agente de detección de fraude.
