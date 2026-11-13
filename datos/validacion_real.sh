#!/usr/bin/env bash
# Mide la API real con carga abierta (llegadas Poisson) para varios tamaños de
# pool y tasas. Sirve para validar y ajustar el simulador (simulacion/ajustar_kappa.py).
#
# Sin Docker (API local):   bash datos/validacion_real.sh
# Con Docker Desktop, la API se recrea con cada pool, p. ej. en PowerShell:
#     $env:DB_POOL_SIZE=5; docker compose up -d --force-recreate api
#     python datos/generar_carga.py abierto --rps 200 --seg 25 --etiqueta pool5
# (la etiqueta debe ser pool<N>, donde N es el DB_POOL_SIZE usado)
set -e
SEG="${SEG:-25}"
COMBOS="${@:-10:100 10:150 10:200 5:200 2:200}"
mkdir -p datos/real
for c in $COMBOS; do
  POOL="${c%%:*}"; RPS="${c##*:}"
  echo "== pool $POOL a $RPS req/s"
  DB_POOL_SIZE=$POOL TELEMETRY_CSV="datos/real/telemetry_pool${POOL}_${RPS}rps.csv" \
    python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --log-level warning >/dev/null 2>&1 &
  PID=$!
  for i in $(seq 1 40); do curl -s localhost:8000/health >/dev/null 2>&1 && break; sleep 0.5; done
  python3 datos/generar_carga.py abierto --rps "$RPS" --seg "$SEG" --etiqueta "pool${POOL}"
  sleep 2
  kill -9 $PID 2>/dev/null || true; sleep 1
done
