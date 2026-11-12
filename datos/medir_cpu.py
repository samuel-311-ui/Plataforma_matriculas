"""
Mide el tiempo de CPU del proceso de la API por tipo de petición (secuencial, sin congestión).

Sirve para separar, dentro del tiempo que una petición pasa en la API, la parte que
consume CPU de Python (compite por el GIL, por lo que solo una a la vez avanza) de la
parte que solo espera a PostgreSQL (E/S).

Solo Linux (lee /proc). Con la API local:   python datos/medir_cpu.py --pid <PID de uvicorn>
Salida: datos/cpu_por_peticion.json
Si no se ejecuta, simulacion/calibrar.py asume que toda la petición consume CPU.
"""
import argparse
import asyncio
import json
import os
import random
import sys
import time

import aiohttp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generar_carga import preparar, una_peticion, RAIZ   # noqa: E402

TICKS = os.sysconf("SC_CLK_TCK")


def cpu_segundos(pid):
    with open(f"/proc/{pid}/stat") as f:
        campos = f.read().rsplit(")", 1)[1].split()
    return (int(campos[11]) + int(campos[12])) / TICKS


async def main(pid, n):
    pares = await preparar()
    res = {}
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=1)) as s:
        for tipo in ("consulta", "matricula"):
            for _ in range(200):
                r = await una_peticion(s, tipo, pares)
                await r.read()
            await asyncio.sleep(2.0)
            c0, t0 = cpu_segundos(pid), time.perf_counter()
            for _ in range(n):
                r = await una_peticion(s, tipo, pares)
                await r.read()
            c1, t1 = cpu_segundos(pid), time.perf_counter()
            res[tipo] = {"cpu_ms": (c1 - c0) / n * 1000, "reloj_ms": (t1 - t0) / n * 1000, "n": n}
            print(tipo, res[tipo])
    pares.guardar()
    with open(os.path.join(RAIZ, "datos", "cpu_por_peticion.json"), "w") as f:
        json.dump(res, f, indent=2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--n", type=int, default=3000)
    a = ap.parse_args()
    asyncio.run(main(a.pid, a.n))
