# Configuración global del modelo SimPy - Grupo 4
SIM_TIME = 480          # Horizonte temporal: 8 horas (480 minutos)
WARMUP_TIME = 60        # Calentamiento (minutos)
NUM_REPLICAS = 30       # Réplicas estocásticas requeridas (N >= 30)

# Parámetros del Servidor y Base de Datos (Alineados)
POOL_SIZE_BASE = 10     # Política actual (Línea Base)
POOL_SIZE_ALT = 15      # Política alternativa (Propuesta de ingeniería)
MAX_CONNECTIONS = 100   # Límite físico duro de cola (C6)

# Tiempos de servicio derivados de telemetría (convertidos a segundos)
VAL_TIME_MEAN = 0.30    # 0.30 segundos por solicitud
VAL_TIME_STD = 0.05

# Tasa de llegada en horas pico (1.0 solicitudes/segundo)
LAMBDA_PICO = 1.0