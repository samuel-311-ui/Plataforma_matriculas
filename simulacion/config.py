"""Parámetros del modelo SimPy - Grupo 4 (Plataforma de matrículas).

Todo lo que viene de la medición (tiempos de servicio) NO está aquí: lo genera
calibrar.py en parametros.json a partir de datos/telemetry_log.csv.
Aquí solo viven los supuestos de la Entrega 1 y los parámetros de diseño.
"""
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
RESULTADOS = os.path.join(RAIZ, "simulacion", "resultados")
FIGURAS = os.path.join(RAIZ, "docs", "figuras")
PARAMETROS = os.path.join(RAIZ, "simulacion", "parametros.json")

# --- Réplicas estocásticas (rúbrica: N >= 30) -------------------------------
NUM_REPLICAS = 30
SEMILLA_BASE = 42                     # semillas 42..71

# --- Servidor y base de datos (Entrega 1 y restricción C6) ------------------
HILOS_POR_REPLICA = 40                # hilos del threadpool de FastAPI/anyio
POOL_SIZE_BASE = 10                   # política actual (E1)
MAX_OVERFLOW = 0
MAX_CONNECTIONS = 100
CONEXIONES_RESERVADAS = 3
CONEXIONES_USABLES = MAX_CONNECTIONS - CONEXIONES_RESERVADAS   # 97 (C6)
POOL_TIMEOUT = 10.0                   # s, espera máxima por conexión

# --- Comportamiento del cliente (Entrega 1, C7) -----------------------------
T_CLIENTE = 10.0                      # s, timeout del cliente
K_REINTENTOS = 3
PAUSA_REINTENTO_MEDIA = 5.0           # s, exponencial
ESPERA_CONSULTA_MEDIA = 20.0          # s, lognormal
ESPERA_CONSULTA_CV = 0.5
P_MATRICULA = 0.6                     # prob. de matricular tras consultar

# --- Escenarios -------------------------------------------------------------
N_BASE = 3000                         # estudiantes de la Entrega 1
N_ESTRES = 24000                      # escenario de estrés (8x)
HORIZONTE = 7200.0                    # s (2 h)
FRAC_PICO = 0.70                      # 70 % llegan U[0, 600] s, 30 % exp(tau=1800)
VENTANA_PICO = 600.0
TAU_COLA = 1800.0

# --- SLA (rúbrica) ----------------------------------------------------------
SLA_P95 = 2.0                         # s
SLA_ABANDONO = 0.03
UTIL_MIN, UTIL_MAX = 0.70, 0.85

# --- Parámetro ajustado contra el sistema real (ajustar_kappa.py) ----------
KAPPA_DEFECTO = 1.3                   # inflación de CPU por contención (se reajusta)
