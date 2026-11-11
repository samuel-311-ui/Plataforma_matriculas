# Informe Final — [Plataforma_Matriculas]
- **Curso:** Modelos y Simulación (2026-2) — I.U. Pascual Bravo
- **Grupo:** Grupo [N]
- **Repositorio:** []
- **Comando de despliegue API:** `docker compose up --build -d`
- **Comando de ejecución SimPy:** `python simulacion/main.py`
- | Integrante | Correo Institucional | Rol Ejecutado | Commits Principales
(Módulos) |
| :--- | :--- | :--- | :--- |
| <span type="placeholder" placeholder-type="person"></span> |
correo1@pascualbravo.edu.co | Modelado DES / SimPy | `simulacion/` |
| <span type="placeholder" placeholder-type="person"></span> |
correo2@pascualbravo.edu.co | Infraestructura / API / Telemetría |
`sistema_real/`, `docker-compose.yml` |
| <span type="placeholder" placeholder-type="person"></span> |
correo3@pascualbravo.edu.co | Análisis Estadístico / Contraste M/M/c |
`analisis/`, `docs/` |
## 1. Resumen Ejecutivo
[Máximo 1 párrafo: problema abordado, políticas comparadas en el simulador
y decisión final de ingeniería respaldada por el KPI principal.]
## 2. Contexto del Sistema y Subsanación de la Entrega 1
### 2.1 Dinámica del Sistema (Qué fluye, qué espera, qué se satura)
- **Entidades que fluyen:** solicitudes HTTP de estudiantes, que llegan desde Streamlit (o directamente a la API en las pruebas de carga). Tipos según el costo en base de datos:
o	Lectura: GET /estudiantes, GET /asignaturas, GET /matriculas.
o	Matrícula: POST /matriculas. Es la más costosa: 2 SELECT por clave primaria.
o	Cancelación: DELETE /matriculas?matricula_id=ID.
o	Registro: POST /estudiantes, POST /asignaturas.
o	Salud: GET /health (un SELECT 1).

- **Recursos y colas de contención:** Recurso:Hilos de atención por réplica de la API
  Capacidad en código:40
  Disciplina: Cola FIFO del threadpool
  -Recurso:Pool de conexiones por réplica
  Capacidad en codigo:DB_POOL_SIZE = 5
  Disciplina: La solicitud espera hasta DB_POOL_TIMEOUT = 30 s por una conexión libre
  -Recurso: Conexiones extra sobre el pool
  Capacidad en codigo: DB_MAX_OVERFLOW = 0
  Disciplina: No hay conexiones adicionales
  -Recurso: Conexiones de PostgreSQL
  Capacidad en codigo: max_connections = 20 (≈17 utilizables por la API)
  Disciplina: Rechazo al agotarse
  -Recurso: Bloqueo de fila de la asignatura
  Capacidad en codigo: 1 por asignatura
  Disciplina: El UPDATE de cupos serializa las matrículas concurrentes sobre la misma asignatura hasta el COMMIT
- **Límite físico duro (C6) y comportamiento de agentes (C7):** [Umbral
físico modelado y regla de abandono/reintento]
