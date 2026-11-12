"""Corre TODOS los experimentos del informe. Un solo comando:

    python simulacion/main.py            (o:  cd simulacion && python main.py)

Cada experimento usa N = 30 réplicas independientes (semillas 42..71). Escribe un CSV por
experimento en simulacion/resultados/ (una fila por réplica). Después, analisis/ calcula
medias, IC95 %, contraste M/M/c y figuras a partir de esos CSV.
Opciones:  --rapido (5 réplicas, para probar)   --solo nombre1,nombre2
"""
import argparse
import itertools
import os
import sys
import time
from multiprocessing import Pool

import pandas as pd

import config as C
import modelo

P = None


def _init():
    global P
    P = modelo.cargar_parametros()


def _params(mundo):
    return P if mundo == "medido" else modelo.parametros_e1(P)


def _tarea(t):
    """t = (experimento, claves, semilla). Devuelve una fila de resultados."""
    exp, cfg, semilla = t
    cfg = dict(cfg)
    mundo = cfg.pop("mundo")
    kind = cfg.pop("kind")
    if kind == "estudiantes":
        n, perfil = cfg.pop("N"), cfg.pop("perfil", "pico60")
        s = modelo.Sistema(_params(mundo), semilla=semilla, **cfg)
        m = s.correr_estudiantes(n, perfil=perfil)
    elif kind == "mmc":
        mu_media = cfg.pop("media_servicio")
        p = modelo.parametros_e1(P, mu_media, mu_media)
        s = modelo.Sistema(p, semilla=semilla, **cfg)
        m = s.correr_abierto(32, 3600, timeout=1e9, calentamiento=300, hasta=3600)
    else:  # abierto
        rps, seg = cfg.pop("rps"), cfg.pop("seg")
        timeout = cfg.pop("timeout", C.T_CLIENTE)
        s = modelo.Sistema(_params(mundo), semilla=semilla, **cfg)
        m = s.correr_abierto(rps, seg, timeout=timeout, calentamiento=seg * 0.2, hasta=seg * 1.5)
    return {"experimento": exp, "mundo": mundo, "semilla": semilla,
            **{k: v for k, v in t[1].items() if k not in ("mundo", "kind")}, **m}


def definir():
    E = {}
    # 1. Línea base de la Entrega 1 con tiempos MEDIDOS y con los SUPUESTOS de la E1
    E["e1_base"] = [dict(mundo=m, kind="estudiantes", N=C.N_BASE, replicas=1, pool=10)
                    for m in ("medido", "e1")]
    # 2. Contraste M/M/10 (lambda=32, mu=4) contra Erlang C
    E["mmc_e1"] = [dict(mundo="e1", kind="mmc", media_servicio=0.25, replicas=1, pool=10)]
    # 3. Sensibilidad a la demanda (supuestos E1): ¿dónde se rompe la política actual?
    E["sens_N_e1"] = [dict(mundo="e1", kind="estudiantes", N=n, replicas=1, pool=10)
                      for n in (3000, 3750, 4500, 6000, 9000, 12000)]
    # 4. Malla réplicas x pool bajo estrés (supuestos E1), solo configuraciones factibles (C6)
    E["malla_e1"] = [dict(mundo="e1", kind="estudiantes", N=6000, replicas=r, pool=p)
                     for r in (1, 2, 3, 4, 6) for p in (5, 10, 15, 20) if r * p <= C.CONEXIONES_USABLES]
    # 5. Variante: trabajo huérfano (el servidor termina peticiones que el cliente ya abandonó)
    E["huerfanas_e1"] = [dict(mundo="e1", kind="estudiantes", N=6000, replicas=1, pool=10, huerfanas=h)
                         for h in (True, False)]
    # 6. Sistema medido: sensibilidad a la demanda (el cuello de botella es la CPU de Python)
    E["sens_N_medido"] = [dict(mundo="medido", kind="estudiantes", N=n, replicas=1, pool=10, perfil="tabla8")
                          for n in (3000, 30000, 100000, 150000)]
    # 7. Sistema medido: malla réplicas x pool a tasa constante (lazo abierto, T=10 s, sin reintentos)
    E["malla_medido"] = [dict(mundo="medido", kind="abierto", rps=rps, seg=60, replicas=r, pool=p)
                         for rps in (250, 500) for r in (1, 2, 4) for p in (5, 10, 20)
                         if r * p <= C.CONEXIONES_USABLES]
    return E


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true")
    ap.add_argument("--solo", default="")
    a = ap.parse_args()
    reps = 5 if a.rapido else C.NUM_REPLICAS
    E = definir()
    if a.solo:
        E = {k: v for k, v in E.items() if k in a.solo.split(",")}
    os.makedirs(C.RESULTADOS, exist_ok=True)
    if not os.path.exists(C.PARAMETROS):
        sys.exit("Falta parametros.json: ejecute primero  python calibrar.py  y  python ajustar_kappa.py")
    with Pool(max(os.cpu_count() or 1, 1), initializer=_init) as pool:
        for nombre, cfgs in E.items():
            t0 = time.time()
            tareas = [(nombre, c, C.SEMILLA_BASE + i) for c in cfgs for i in range(reps)]
            filas = pool.map(_tarea, tareas, chunksize=1)
            pd.DataFrame(filas).to_csv(os.path.join(C.RESULTADOS, f"{nombre}.csv"), index=False)
            print(f"{nombre}: {len(filas)} corridas en {time.time()-t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
