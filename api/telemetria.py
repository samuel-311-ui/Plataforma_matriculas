"""
Telemetría por petición para calibrar el modelo SimPy.

Por cada petición HTTP se escribe una fila en datos/telemetry_log.csv:

    timestamp    instante de llegada a la API (epoch, s)
    method       método HTTP
    endpoint     ruta
    status_code  código de respuesta
    duration_ms  tiempo total de la petición dentro de la API
    pre_ms       tiempo desde que llega hasta que obtiene una conexión del pool
                 (validación + espera de hilo/CPU + espera de pool)  -> etapas 1 y 2
    hold_ms      tiempo que la petición retiene una conexión del pool
                 (checkout -> checkin)                                -> etapa 3 (BD)

pre_ms y hold_ms se miden con eventos del pool de SQLAlchemy, sin tocar la
lógica de los endpoints. La escritura al CSV la hace un hilo aparte, para no
bloquear el ciclo de eventos de la API (escribir en disco dentro del
middleware añadiría latencia a cada petición y falsearía la medición).
"""
import contextvars
import csv
import os
import threading
import time

from sqlalchemy import event

# Carpeta del CSV: dentro de Docker el volumen ./datos se monta en /app/datos.
LOG_DIR = "/app/datos" if os.path.exists("/app") else "datos"
LOG_FILE = os.getenv("TELEMETRY_CSV", os.path.join(LOG_DIR, "telemetry_log.csv"))
COLUMNAS = ["timestamp", "method", "endpoint", "status_code",
            "duration_ms", "pre_ms", "hold_ms"]

# La conexión se devuelve al pool unos instantes DESPUÉS de que el middleware
# mide la respuesta; se espera este margen (s) antes de escribir la fila para
# que hold_ms ya esté completo.
_MARGEN_CIERRE = 1.5

_registro = contextvars.ContextVar("registro_telemetria", default=None)
_candado = threading.Lock()
_pendientes = []


def nuevo_registro(metodo, ruta):
    """Crea el registro de una petición y lo deja disponible en su contexto."""
    reg = {
        "ts": time.time(), "t0": time.perf_counter(),
        "method": metodo, "endpoint": ruta,
        "status": 0, "total_ms": 0.0, "pre_ms": 0.0, "hold_ms": 0.0,
        "t_fin": None,
    }
    return reg, _registro.set(reg)


def cerrar_registro(reg, token, status):
    """Se llama al terminar la petición: fija estado y tiempo total."""
    _registro.reset(token)
    reg["status"] = status
    reg["total_ms"] = (time.perf_counter() - reg["t0"]) * 1000
    reg["t_fin"] = time.perf_counter()
    with _candado:
        _pendientes.append(reg)
    return reg["total_ms"]


def instrumentar_pool(engine):
    """Mide pre_ms y hold_ms con los eventos checkout/checkin del pool."""

    @event.listens_for(engine, "checkout")
    def _checkout(dbapi_con, con_record, con_proxy):
        ahora = time.perf_counter()
        reg = _registro.get()
        con_record.info["t_checkout"] = ahora
        con_record.info["reg"] = reg
        if reg is not None and reg["pre_ms"] == 0.0:
            reg["pre_ms"] = (ahora - reg["t0"]) * 1000

    @event.listens_for(engine, "checkin")
    def _checkin(dbapi_con, con_record):
        t0 = con_record.info.pop("t_checkout", None)
        reg = con_record.info.pop("reg", None)
        if reg is not None and t0 is not None:
            reg["hold_ms"] += (time.perf_counter() - t0) * 1000


def _escritor():
    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
    nuevo = not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0
    with open(LOG_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(COLUMNAS)
            f.flush()
        while True:
            time.sleep(0.5)
            ahora = time.perf_counter()
            with _candado:
                listos = [r for r in _pendientes
                          if r["t_fin"] is not None and ahora - r["t_fin"] > _MARGEN_CIERRE]
                if listos:
                    ids = {id(r) for r in listos}
                    _pendientes[:] = [r for r in _pendientes if id(r) not in ids]
            for r in listos:
                w.writerow([f"{r['ts']:.4f}", r["method"], r["endpoint"], r["status"],
                            f"{r['total_ms']:.3f}", f"{r['pre_ms']:.3f}", f"{r['hold_ms']:.3f}"])
            if listos:
                f.flush()


def iniciar_escritor():
    hilo = threading.Thread(target=_escritor, daemon=True, name="telemetria-csv")
    hilo.start()
    return hilo
