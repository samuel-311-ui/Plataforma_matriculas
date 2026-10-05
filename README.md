# Plataforma_matriculas
Plataforma de Matrícula Académica en Picos de Inscripción
Descripción

Este proyecto desarrolla un prototipo de una plataforma de matrícula académica diseñada para analizar el comportamiento de un sistema durante periodos de alto flujo de usuarios.

El proyecto busca simular un escenario en el que múltiples estudiantes realizan solicitudes de consulta y matrícula de asignaturas simultáneamente. Estas solicitudes pueden generar colas, tiempos de espera y saturación de recursos, especialmente en la API y en las conexiones disponibles hacia la base de datos.

El sistema real se implementa mediante una arquitectura compuesta por Streamlit, FastAPI y PostgreSQL, desplegada utilizando Docker. Posteriormente, este sistema servirá como referencia para construir un modelo de simulación de eventos discretos (DES) utilizando SimPy.

# Objetivo

Analizar mediante simulación de eventos discretos el comportamiento de una plataforma de matrícula académica durante picos de inscripción, evaluando diferentes configuraciones de recursos para determinar cuáles permiten mantener tiempos de respuesta aceptables.

Las principales variables de decisión son:

Número de réplicas de la API.
Tamaño del pool de conexiones de PostgreSQL.
Arquitectura

La aplicación utiliza la siguiente arquitectura:

┌─────────────────┐
│    Estudiante   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Streamlit    │
│   Interfaz Web  │
│     :8501       │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│     FastAPI     │
│    REST API     │
│      :8000      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│      :5432      │
└─────────────────┘

Estructura del proyecto
Plataforma_matriculas/
│
├── api/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│
├── streamlit/
│   └── app.py
│
├── simulacion/
│
├── datos/
│
├── analisis/
│
├── docs/
│
├── Dockerfile.api
├── Dockerfile.streamlit
├── docker-compose.yml
├── requirements-api.txt
├── requirements-streamlit.txt

└── README.md


La API proporciona los siguientes endpoints principales:

Método	Endpoint	Descripción
GET	/	Verificar que la API está funcionando
POST	/estudiantes	Registrar un estudiante
GET	/estudiantes	Consultar estudiantes
POST	/asignaturas	Registrar una asignatura
GET	/asignaturas	Consultar asignaturas
POST	/matriculas	Registrar una matrícula

<!--

Antes de ejecutar el proyecto se necesita tener instalado:

Docker Desktop
Git
Visual Studio Code
1. Clonar el repositorio
git clone https://github.com/samuel-311-ui/Plataforma_matriculas

Entrar a la carpeta:

cd Plataforma_matriculas
2. Crear el archivo de variables de entorno


Ejemplo:

POSTGRES_USER=matricula_user
POSTGRES_PASSWORD=matricula_password
POSTGRES_DB=matricula_db
POSTGRES_HOST=db
POSTGRES_PORT=5432
3. Construir y ejecutar los servicios
docker compose up --build

Docker iniciará los siguientes servicios:

db
api
streamlit
4. Acceder a la aplicación

Streamlit:

http://localhost:8501

FastAPI:

http://localhost:8000

Documentación de la API:

http://localhost:8000/docs
Detener los servicios

Para detener los contenedores:

docker compose down
