# 01 — Requerimientos

Antes de comenzar el workshop, asegúrate de tener todos los elementos de esta lista listos. Al finalizar esta sección podrás ejecutar el código por primera vez y ver el mensaje de bienvenida del sistema.

---

## 1. Software requerido

### Git

Necesitas Git para clonar el repositorio del workshop.

Verifica que está instalado:

```sh
git --version
```

Resultado esperado: `git version 2.x.x` o superior.

Si no está instalado, descárgalo desde [git-scm.com/downloads](https://git-scm.com/downloads) e instálalo con las opciones por defecto.

---

### Python 3.11 o superior

Verifica la versión:

```sh
python --version
```

Resultado esperado: `Python 3.11.x` o superior.

Si no está instalado, descárgalo desde [python.org/downloads](https://python.org/downloads). Durante la instalación, marca la opción **"Add Python to PATH"**.

---

### Visual Studio Code

Descarga e instala VS Code desde [code.visualstudio.com](https://code.visualstudio.com) si aún no lo tienes.

---

## 2. GitHub Copilot en VS Code

GitHub Copilot se usará durante el workshop para explorar y entender el código.

### Instalar la extensión

1. Abre VS Code.
2. Ve al panel de **Extensiones** (`Ctrl+Shift+X`).
3. Busca `GitHub Copilot`.
4. Instala la extensión oficial de **GitHub**.
5. Instala también **GitHub Copilot Chat** si no se instala automáticamente.
6. Al pedirte que inicies sesión, usa tu cuenta de GitHub.

> Si tu organización ya te provee una licencia de Copilot, la extensión la detectará automáticamente al iniciar sesión.

---

## 3. Cuenta GitHub y acceso a GitHub Models

### Verificar acceso a GitHub Models

1. Inicia sesión en [github.com](https://github.com).
2. Ve a [github.com/marketplace/models](https://github.com/marketplace/models).
3. La página debe mostrar una galería de modelos disponibles (GPT-4o, Llama, Phi, etc.).

Si la página muestra un mensaje de acceso restringido, verifica que:
- Tu cuenta de GitHub esté activa y verificada por correo.
- No sea una cuenta recién creada (puede requerir algunas horas de espera).

---

## 4. Crear el Personal Access Token (PAT)

El token permite que el código del workshop se autentique con GitHub Models para llamar al modelo de lenguaje.

### Pasos para crear el token

1. En GitHub, haz clic en tu foto de perfil (esquina superior derecha).
2. Selecciona **Settings**.
3. En el menú izquierdo, desplázate hasta el final y selecciona **Developer settings**.
4. Selecciona **Personal access tokens → Fine-grained tokens**.
5. Haz clic en **Generate new token**.
6. Completa los campos:

   | Campo | Valor |
   |---|---|
   | **Token name** | `workshop-agents` |
   | **Expiration** | 7 days |
   | **Resource owner** | Tu usuario (por defecto) |
   | **Repository access** | Public Repositories (read-only) |
   | **Permissions** | Sin permisos adicionales requeridos |

7. Haz clic en **Generate token**.
8. **Copia el token inmediatamente** — GitHub solo lo muestra una vez.

> Guarda el token en un lugar seguro mientras dure el workshop (por ejemplo, un bloc de notas temporal). No lo compartas ni lo subas a ningún repositorio.

---

## 5. Clonar el repositorio

Abre una terminal y ejecuta:

```sh
git clone https://github.com/GSaraySWO/AgentsWorkshopMAF
cd AgentsWorkshopMAF
```

Abre la carpeta en VS Code:

```sh
code .
```

---

## 6. Crear el entorno virtual e instalar las dependencias

Crea un entorno virtual de Python llamado `labenv` dentro de la carpeta `Python/`:

```sh
python -m venv labenv
```

Activa el entorno:

```sh
# Windows (PowerShell)
labenv\Scripts\Activate.ps1

# Mac / Linux
source labenv/bin/activate
```

Verifica que el prompt de tu terminal cambia y muestra `(labenv)` al inicio. Esto indica que el entorno está activo.

> **Importante:** Debes activar el entorno cada vez que abras una nueva terminal para trabajar con este proyecto.

Instala los paquetes necesarios:

```sh
pip install -r requirements.txt
```

Resultado esperado: una lista de paquetes instalados sin errores. Los paquetes principales son:

| Paquete | Propósito |
|---|---|
| `openai` | Comunicación con GitHub Models (API compatible con OpenAI) |
| `agent-framework` | Microsoft Agent Framework SDK (backend Azure) |
| `python-dotenv` | Carga de variables desde el archivo `.env` |
| `azure-identity` | Autenticación con Azure (para el backend de Foundry) |
| `opentelemetry-semantic-conventions-ai` | Trazabilidad de agentes IA |

---

## 7. Configurar el archivo `.env`

El archivo `.env` contiene las credenciales y opciones de configuración del workshop. El repositorio incluye un archivo `.env.example` como plantilla.

### Copiar la plantilla

```sh
# Windows (PowerShell)
Copy-Item .env.example .env

# Mac / Linux
cp .env.example .env
```

### Editar el archivo `.env`

Abre `.env` en VS Code y completa los valores:

```ini
# Backend a usar: github (para este workshop) o azure
AGENT_BACKEND="github"

# Activar o desactivar la memoria entre ejecuciones (true/false)
USE_MEMORY=false

# Configuración de GitHub Models
GITHUB_TOKEN="<pega aquí tu token del paso 4>"
GITHUB_MODEL="openai/gpt-4o-mini"
GITHUB_ENDPOINT="https://models.github.ai/inference"
```

### Descripción de cada variable

| Variable | Descripción | Valor inicial |
|---|---|---|
| `AGENT_BACKEND` | Qué backend de IA usar | `"github"` |
| `USE_MEMORY` | Activar/desactivar memoria entre sesiones | `false` |
| `GITHUB_TOKEN` | Tu Personal Access Token de GitHub | *(el que copiaste en el paso 4)* |
| `GITHUB_MODEL` | Modelo de lenguaje a usar | `"openai/gpt-4o-mini"` |
| `GITHUB_ENDPOINT` | URL base de la API de GitHub Models | `"https://models.github.ai/inference"` |

> Empieza con `USE_MEMORY=false` — activaremos la memoria más adelante en el archivo [04-PruebasConMemoria.md](04-PruebasConMemoria.md).

---

## 8. Verificación final

Ejecuta el siguiente comando sin argumentos para confirmar que todo está configurado correctamente (con el entorno activado):

```sh
python agents.py
```

Debes ver una salida similar a esta:

```
[Orchestrator] Usage: python agents.py <transaction_name>
  Example: python agents.py transactionA
  Available files in data/: transactionA.json, transactionB.json, transactionC.json, transactionD.json, transactionE.json
```

Si aparece este mensaje, el entorno está listo. Continúa con [02-Exploracion.md](02-Exploracion.md).

---

## Resumen de verificaciones

| Elemento | Comando de verificación | Resultado esperado |
|---|---|---|
| Git | `git --version` | `git version 2.x.x` |
| Python | `python --version` | `Python 3.11.x` o superior |
| Entorno activado | Windows: `labenv\Scripts\Activate.ps1` / Mac·Linux: `source labenv/bin/activate` | Prefijo `(labenv)` visible en el terminal |
| Dependencias | `pip list` | `openai`, `agent-framework`, `python-dotenv` visibles |
| `.env` | Revisar que `GITHUB_TOKEN` no sea `<pega aquí...>` | Token real asignado |
| Entorno completo | `python agents.py` | Mensaje de uso con lista de transacciones |
