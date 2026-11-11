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
samuel.zapata599pascualbravo.edu.co | Modelado DES / SimPy | `simulacion/` |
| <span type="placeholder" placeholder-type="person"></span> |
simon.restrepo405@pascualbravo.edu.co | Infraestructura / API / Telemetría |
`sistema_real/`, `docker-compose.yml` |
| <span type="placeholder" placeholder-type="person"></span> |
felipe.hurtado796@pascualbravo.edu.co | Análisis Estadístico / Contraste M/M/c |
`analisis/`, `docs/` |
## 1. Resumen Ejecutivo
[Una plataforma de matrícula académica recibe picos de solicitudes simultáneas (consultas, matrículas y cancelaciones) que compiten por las conexiones a PostgreSQL y por los cupos de las asignaturas, lo que genera colas, tiempos de espera y rechazos. Se construyó un prototipo real contenerizado (Streamlit + FastAPI + PostgreSQL en Docker) que registra telemetría por petición, y con ella se calibró un modelo de simulación de eventos discretos en SimPy.]
## 2. Contexto del Sistema y Subsanación de la Entrega 1
### 2.1 Dinámica del Sistema (Qué fluye, qué espera, qué se satura)
- **Entidades que fluyen:** solicitudes HTTP de estudiantes, que llegan desde Streamlit (o directamente a la API en las pruebas de carga). Tipos según el costo en base de datos:
o	Lectura: GET /estudiantes, GET /asignaturas, GET /matriculas.
o	Matrícula: POST /matriculas. Es la más costosa: 2 SELECT por clave primaria.
o	Cancelación: DELETE /matriculas?matricula_id=ID.
o	Registro: POST /estudiantes, POST /asignaturas.
o	Salud: GET /health (un SELECT 1).
### 2.2 Tabla de Subsanación de la Entrega Parcial 1
| Observación / Error en Entrega 1 | Corrección Implementada en la Entrega
Final | Archivo / Línea en el Repositorio |
| :--- | :--- | :--- |
| [Ej. Inconsistencia en tasa μ o falta de SimPy] | [Descripción exacta
del ajuste matemático o de código] | `simulacion/config.py` |
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
- **Límite físico duro (C6) y comportamiento de agentes (C7):**
- C6: PostgreSQL con max_connections=20; la configuración debe cumplir réplicas × (DB_POOL_SIZE + DB_MAX_OVERFLOW) ≤ 17.
- C7: No hay regla de abandono
## 3. Arquitectura del Prototipo, Telemetría y Parámetros Calibrados
### 3.1 Resumen de Telemetría del Sistema Real Contenerizado
Arquitectura desplegada con docker compose up --build -d: streamlit (:8501) → api FastAPI (:8000) → db PostgreSQL 16 (:5432, max_connections=20).
El middleware medir_tiempo (api/main.py) escribe una línea por petición en los logs de la API con el formato METRICA,<método>,<ruta>,<status>,<duración_ms> (visible con docker logs matricula_api) y agrega el header X-Process-Time-ms a cada respuesta. Esas líneas se extraen y se consolidan en datos/telemetry_log.csv.
Aspectos a tener en cuenta al interpretar los datos:
•	La duración medida incluye la espera por un hilo y por una conexión del pool, no solo el tiempo de servicio. Para estimar el tiempo de servicio puro hay que medir con carga baja (sin cola) y, para estimar la espera, con carga alta.
•	No incluye la cola previa a que Uvicorn acepte la petición ni la latencia de red.
•	La interfaz de Streamlit solo expone estudiantes; las pruebas de carga con matrículas deben generarse llamando directamente a la API.
### 3.2 Parámetros y Distribuciones de Entrada del Modelo SimPy
| Parámetro | Etapa / Proceso | Distribución y Parámetros Exactos | Unidad
| Fuente / Evidencia en Telemetría o Literatura |
| :--- | :--- | :--- | :--- | :--- |
| Tasa de llegada (Valle / Pico) | Entrada | Poisson no homogénea (λ1=...,
λ2=...) | req/min | [Fuente] |
| Tiempo de servicio Etapa 1 | API / Validación | Lognormal (μ=..., σ=...)
| s | `datos/telemetry_log.csv` |
## 4. Diseño Experimental y Contraste Analítico (M/M/c vs. SimPy)
- **Horizonte simulado:** [Ej. 8 horas = 480 min]
- **Periodo de calentamiento (Warm-up):** [Ej. 60 min]
- **Número de réplicas independientes (R):** [Ej. 30 réplicas con semillas
`42..71`]
### 4.1 Tabla de Validación Analítica (Régimen Estacionario Exponencial)
| Métrica | Modelo Analítico M/M/c | SimPy Modo Markoviano (Media ± IC
95%) | Diferencia Relativa (%) |
| :--- | :---: | :---: | :---: |
| Utilización (ρ) | | | |
| Longitud media de cola (Lq) | | | |
| Tiempo medio de espera en cola (Wq) | | | |
| Tiempo medio en el sistema (W) | | | |
**Análisis de divergencia al activar la dinámica real:** [Explicar en 1
párrafo cómo cambian las métricas cuando se activan las llegadas en
ráfaga, distribuciones no exponenciales, abandonos y reintentos frente al
M/M/c.]
## 5. Resultados de la Simulación y Evaluación de Políticas de Decisión
### 5.1 Comparación Cuantitativa de Escenarios
| KPI (con unidad) | Umbral SLA | Política Actual (Media ± IC 95% | p95) |
Política Alternativa 1 (Media ± IC 95% | p95) | Política Alternativa 2
(Media ± IC 95% | p95) | ¿Cumple SLA? |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Tiempo de respuesta (s) | p95 < 2.0 s | | | | |
| Tasa de abandono / rechazo (%) | < 3.0 % | | | | |
| Utilización del cuello de botella (%) | 70% - 85% | | | | |
### 5.2 Análisis de las Preguntas de Decisión
- **Respuesta a Pregunta de Decisión 1:** [Análisis directo con cifras e
interpretación de las gráficas enlazadas.]
- **Respuesta a Pregunta de Decisión 2:** [Análisis directo con cifras e
interpretación del cuello de botella.]
## 6. Recomendación de Ingeniería y Declaración de Uso de IA
### 6.1 Recomendación Técnica Final
[Especificar qué configuración/política debe desplegarse en producción y
por qué.]
### 6.2 Declaración de Uso de Inteligencia Artificial
| Herramienta de IA | Secciones / Módulos donde se utilizó | Qué verificó,
corrigió y validó el equipo |
| :--- | :--- | :--- |
| [Ej. Gemini / Claude / Copilot] | [Ej. Refactorización de clases SimPy y
gráficas] | [Verificación manual de ecuaciones y pruebas unitarias] |



