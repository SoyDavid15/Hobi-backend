# Hobi Backend - API REST (FastAPI)

Backend de la aplicación **Hobi**, encargado de la autenticación con Supabase, gestión de hobbies y generación de retos diarios utilizando la API de Google Gemini.

---

## 🛠️ Tecnologías y Arquitectura
- **Framework**: FastAPI (Python 3.11)
- **Servidor ASGI**: Uvicorn
- **Base de Datos y Autenticación**: Supabase
- **IA Generativa**: Google GenAI SDK (Gemini)
- **Infraestructura Cloud**: Microsoft Azure App Service (Linux) - Despliegue nativo sin Docker
- **CI/CD**: GitHub Actions

---

## 📋 Registro de Cambios y Configuración para Azure

### 1. Puerto Dinámico (Cero puertos hardcodeados)
- Modificado [main.py](file:///c:/Users/kayno/OneDrive/Desktop/Escritorio/Trabajo/CLIKEA/Hobi/Backend/main.py) para resolver el puerto dinámicamente mediante variables de entorno:
  ```python
  port = int(os.getenv("PORT", os.getenv("WEBSITES_PORT", "8000")))
  ```
- Prioridad de resolución:
  1. `PORT`: Variable estándar en la nube (Render, Azure Container, etc.).
  2. `WEBSITES_PORT`: Variable inyectada por Azure App Service.
  3. `8000`: Valor de respaldo (*fallback*) para ejecución local en caso de que no exista ninguna variable.

### 2. Manejo Seguro de Nulos en Supabase
- Corregido [hobbies.py](file:///c:/Users/kayno/OneDrive/Desktop/Escritorio/Trabajo/CLIKEA/Hobi/Backend/hobbies.py) para validar la existencia de `res` y `res.data` (`if res and res.data:`):
  - Evita excepciones de tipo `AttributeError: 'NoneType' object has no attribute 'data'` cuando el usuario no tiene retos o hobbies previos.

### 3. Plantilla de Variables de Entorno
- Creado [.env.example](file:///c:/Users/kayno/OneDrive/Desktop/Escritorio/Trabajo/CLIKEA/Hobi/Backend/.env.example) como referencia para variables en local y Azure:
  ```env
  PORT=8000
  GEMINI_KEY=tu_api_key_de_gemini
  SUPABASE_URL=https://tu-proyecto.supabase.co
  SUPABASE_ANON_KEY=tu_anon_key_de_supabase
  SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key_de_supabase
  ```

### 4. Automatización CI/CD con GitHub Actions
- Configurado [.github/workflows/azure-webapps-python.yml](file:///c:/Users/kayno/OneDrive/Desktop/Escritorio/Trabajo/CLIKEA/Hobi/Backend/.github/workflows/azure-webapps-python.yml):
  - **App Name**: `hobi-csc4gqdaahejgbgh`
  - **Python Version**: `3.11`
  - Despliegue automático a Azure App Service con cada `git push` a la rama `master`.

### 5. Conexión del Frontend
- Actualizada la URL base en el cliente móvil Expo ([src/lib/api.ts](file:///c:/Users/kayno/OneDrive/Desktop/Escritorio/Trabajo/CLIKEA/Hobi/Hobi/src/lib/api.ts)):
  ```typescript
  export const API_URL =
    process.env.EXPO_PUBLIC_API_URL ?? 'https://hobi-csc4gqdaahejgbgh.centralus-01.azurewebsites.net';
  ```

---

## 💻 Ejecución en Local

1. **Crear y activar entorno virtual**:
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En Linux/Mac:
   source venv/bin/activate
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar archivo `.env`**:
   Crear un archivo `.env` basado en `.env.example` con las claves reales.

4. **Iniciar el servidor**:
   ```bash
   python main.py
   # o alternativamente:
   uvicorn main:app --reload
   ```

---

## ☁️ Configuración en Microsoft Azure App Service

- **Publish**: `Code` (Python 3.11 / Linux).
- **Startup Command** (*Settings > Configuration > General settings*):
  ```bash
  uvicorn main:app --host 0.0.0.0 --port 8000
  ```
  *(o `python main.py`)*
- **Variables de Entorno Requeridas** (*Settings > Environment variables*):
  - `GEMINI_KEY`
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SCM_DO_BUILD_DURING_DEPLOYMENT`: `true`

---

## 📡 Endpoints de la API

| Ruta | Método | Autenticación | Descripción |
| :--- | :---: | :---: | :--- |
| `/` | `GET` | No | Health check del servicio (`{"status": "ok"}`) |
| `/openapi.json` | `GET` | No | Especificación OpenAPI de FastAPI |
| `/docs` | `GET` | No | Documentación interactiva Swagger UI |
| `/message` | `GET` | Sí (`Bearer Token`) | Obtiene o genera el reto diario del usuario |
| `/hobbies` | `GET` | Sí (`Bearer Token`) | Lista los hobbies del usuario autenticado |
| `/hobbies/{hobby_id}` | `POST` | Sí (`Bearer Token`) | Asocia un nuevo hobby al usuario |
| `/hobbies/{hobby_id}` | `DELETE` | Sí (`Bearer Token`) | Elimina un hobby del usuario |
