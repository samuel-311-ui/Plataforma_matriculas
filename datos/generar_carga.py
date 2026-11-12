"""
Generador de carga para medir la API real (usa solo HTTP, funciona con Docker).

Requisitos:  pip install aiohttp      y la API levantada:  docker compose up --build -d

    python datos/generar_carga.py seed
        Crea estudiantes y asignaturas (cupos casi ilimitados para medir
        rendimiento y no agotamiento de cupos, supuesto S3 de la Entrega 1).

    python datos/generar_carga.py calibrar --n 3000
        Mide el tiempo de servicio SIN congestión: peticiones secuenciales
        (concurrencia 1), n de cada tipo (consulta y matrícula). La telemetría
        queda en datos/telemetry_log.csv (la escribe la API) y la ventana de
        medición en datos/calibracion_meta.json.

    python datos/generar_carga.py abierto --rps 150 --seg 25 --etiqueta pool10
        Carga de llegadas Poisson (lazo abierto) con la mezcla de la Entrega 1
        (62.5 % consultas / 37.5 % matrículas). Guarda la latencia medida por
        el cliente en datos/real/cliente_<etiqueta>_<rps>rps.csv; se usa para
        validar el simulador contra el sistema real.

Tipos de solicitud (Entrega 1): consulta = GET /asignaturas;
matrícula = POST /matriculas.
"""
import argparse
import asyncio
import csv
import json
import os
import random
import time

import aiohttp

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N_ESTUDIANTES = 3000
N_ASIGNATURAS = 40
CUPOS = 10 ** 7
P_MATRICULA = 0.375            # 1 consulta + 0.6 matrículas por estudiante -> 0.6/1.6
ESTADO = os.path.join(RAIZ, "datos", "estado_carga.json")


# ------------------------------------------------------------------ utilidades
async def ids_existentes(s):
    async with s.get(f"{BASE_URL}/estudiantes") as r:
        est = [x["id"] for x in await r.json()]
    async with s.get(f"{BASE_URL}/asignaturas") as r:
        asg = [x["id"] for x in await r.json()]
    return est, asg


async def seed():
    sem = asyncio.Semaphore(20)
    conn = aiohttp.TCPConnector(limit=40)
    async with aiohttp.ClientSession(connector=conn) as s:
        async def crear(ruta, cuerpo):
            async with sem:
                async with s.post(f"{BASE_URL}{ruta}", json=cuerpo) as r:
                    await r.read()
        tareas = [crear("/estudiantes", {"nombre": f"Estudiante {i}",
                                         "correo": f"est{i}@pascualbravo.edu.co"})
                  for i in range(1, N_ESTUDIANTES + 1)]
        tareas += [crear("/asignaturas", {"codigo": f"ASG{j:03d}", "nombre": f"Asignatura {j}",
                                          "cupos": CUPOS}) for j in range(1, N_ASIGNATURAS + 1)]
        await asyncio.gather(*tareas)
        est, asg = await ids_existentes(s)
    print(f"seed OK: {len(est)} estudiantes, {len(asg)} asignaturas")
    return est, asg


class Pares:
    """Pares (estudiante, asignatura) únicos para no chocar con la restricción UNIQUE.
    El índice se guarda en disco para no repetir pares entre ejecuciones."""

    def __init__(self, est, asg):
        rnd = random.Random(2026)
        self.p = [(e, a) for e in est for a in asg]
        rnd.shuffle(self.p)
        try:
            self.i = json.load(open(ESTADO))["siguiente"]
        except Exception:
            self.i = 0

    def siguiente(self):
        par = self.p[self.i % len(self.p)]
        self.i += 1
        return par

    def guardar(self):
        os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
        json.dump({"siguiente": self.i}, open(ESTADO, "w"))


async def una_peticion(s, tipo, pares):
    if tipo == "consulta":
        return await s.get(f"{BASE_URL}/asignaturas")
    e, a = pares.siguiente()
    return await s.post(f"{BASE_URL}/matriculas", json={"estudiante_id": e, "asignatura_id": a})


async def preparar():
    conn = aiohttp.TCPConnector(limit=1)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=5)) as s:
        est, asg = await ids_existentes(s)
    if len(est) < 100 or len(asg) < 5:
        est, asg = await seed()
    return Pares(est, asg)


# ----------------------------------------------------------------- calibración
async def calibrar(n):
    pares = await preparar()
    rnd = random.Random(7)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=1)) as s:
        for _ in range(300):                       # calentamiento (se descarta por marca de tiempo)
            for tipo in ("consulta", "matricula"):
                r = await una_peticion(s, tipo, pares)
                await r.read()
        await asyncio.sleep(2.5)
        inicio = time.time()
        for _ in range(n):
            orden = ["consulta", "matricula"]
            rnd.shuffle(orden)
            for tipo in orden:
                r = await una_peticion(s, tipo, pares)
                await r.read()
        fin = time.time()
    await asyncio.sleep(3.0)                       # deja que la API termine de escribir el CSV
    pares.guardar()
    json.dump({"inicio_medicion": inicio, "fin_medicion": fin, "n_por_tipo": n},
              open(os.path.join(RAIZ, "datos", "calibracion_meta.json"), "w"), indent=2)
    print(f"calibración terminada: {n} peticiones de cada tipo ({2 * n} en total)")


# ------------------------------------------------------------- carga abierta
async def abierto(rps, seg, etiqueta, semilla):
    pares = await preparar()
    rnd = random.Random(semilla)
    filas = []
    conn = aiohttp.TCPConnector(limit=0)

    async def lanzar(s, tipo, t_prog):
        t0 = time.perf_counter()
        try:
            r = await una_peticion(s, tipo, pares)
            await r.read()
            st = r.status
        except Exception:
            st = 0
        filas.append((t_prog, tipo, st, (time.perf_counter() - t0) * 1000))

    async with aiohttp.ClientSession(connector=conn, timeout=aiohttp.ClientTimeout(total=15)) as s:
        for _ in range(100):
            r = await una_peticion(s, "consulta", pares)
            await r.read()
        tareas, inicio, t = [], time.perf_counter(), 0.0
        while t < seg:
            t += rnd.expovariate(rps)
            espera = inicio + t - time.perf_counter()
            if espera > 0:
                await asyncio.sleep(espera)
            tipo = "matricula" if rnd.random() < P_MATRICULA else "consulta"
            tareas.append(asyncio.create_task(lanzar(s, tipo, t)))
        await asyncio.gather(*tareas)
    pares.guardar()
    salida = os.path.join(RAIZ, "datos", "real", f"cliente_{etiqueta}_{int(rps)}rps.csv")
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    with open(salida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_llegada_s", "tipo", "status", "latencia_ms"])
        w.writerows(sorted(filas))
    print(f"carga abierta {rps} req/s x {seg} s -> {len(filas)} peticiones -> {salida}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed")
    c = sub.add_parser("calibrar")
    c.add_argument("--n", type=int, default=3000)
    a = sub.add_parser("abierto")
    a.add_argument("--rps", type=float, required=True)
    a.add_argument("--seg", type=float, default=25)
    a.add_argument("--etiqueta", default="pool10")
    a.add_argument("--semilla", type=int, default=1)
    args = ap.parse_args()
    if args.cmd == "seed":
        asyncio.run(seed())
    elif args.cmd == "calibrar":
        asyncio.run(calibrar(args.n))
    else:
        asyncio.run(abierto(args.rps, args.seg, args.etiqueta, args.semilla))
