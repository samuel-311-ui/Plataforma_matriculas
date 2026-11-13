"""Ajusta kappa (inflación de CPU por contención) y valida el simulador contra el sistema real.

Real: datos/real/cliente_<etiqueta>_<rps>rps.csv (latencia medida por el cliente, API real).
Ajuste: corridas de carga moderada (<=200 req/s). Validación fuera de muestra: 250-350 req/s
(región de saturación, que NO se usa para ajustar).
Escribe simulacion/resultados/validacion.csv y actualiza kappa en parametros.json.
"""
import glob
import json
import os
import re

import numpy as np
import pandas as pd

import config as C
import modelo

AJUSTE = [("pool10", 100), ("pool10", 150), ("pool10", 200), ("pool5", 200), ("pool2", 200)]
FUERA = [("pool10", 250), ("pool10", 300), ("pool10", 350)]
REPS = 8


def real(etq, rps):
    d = pd.read_csv(os.path.join(C.DATOS, "real", f"cliente_{etq}_{rps}rps.csv"))
    ok = d[d.status == 200].latencia_ms
    return {"n": len(d), "ok": len(ok) / len(d), "media_ms": ok.mean(), "p95_ms": ok.quantile(.95)}


def sim(p, etq, rps, kappa):
    pool = int(etq.replace("pool", ""))
    r = []
    for s in range(REPS):
        m = modelo.Sistema(p, pool=pool, kappa=kappa, semilla=100 + s).correr_abierto(rps, 25)
        r.append(m)
    return {k: float(np.nanmean([x[k] for x in r])) for k in ("ok", "media_ms", "p95_ms")}


def error(p, kappa):
    e = []
    for etq, rps in AJUSTE:
        a, b = real(etq, rps), sim(p, etq, rps, kappa)
        e += [np.log(b["media_ms"] / a["media_ms"]), np.log(b["p95_ms"] / a["p95_ms"])]
    return float(np.sqrt(np.mean(np.square(e))))


def main():
    p = modelo.cargar_parametros()
    malla = np.round(np.arange(1.0, 2.01, 0.1), 2)
    errs = {float(k): error(p, k) for k in malla}
    mejor = min(errs, key=errs.get)
    print("RMSE log por kappa:", {k: round(v, 3) for k, v in errs.items()})
    print("kappa ajustado =", mejor)
    p["kappa"] = mejor
    filas = []
    for grupo, lista in (("ajuste", AJUSTE), ("fuera_de_muestra", FUERA)):
        for etq, rps in lista:
            a, b = real(etq, rps), sim(p, etq, rps, mejor)
            filas.append({"grupo": grupo, "pool": etq, "rps": rps,
                          "ok_real": a["ok"], "ok_sim": b["ok"],
                          "media_real_ms": a["media_ms"], "media_sim_ms": b["media_ms"],
                          "p95_real_ms": a["p95_ms"], "p95_sim_ms": b["p95_ms"]})
    df = pd.DataFrame(filas)
    os.makedirs(C.RESULTADOS, exist_ok=True)
    df.to_csv(os.path.join(C.RESULTADOS, "validacion.csv"), index=False)
    pd.Series(errs).rename("rmse_log").to_csv(os.path.join(C.RESULTADOS, "kappa_malla.csv"))
    print(df.round(3).to_string())
    j = json.load(open(C.PARAMETROS))
    j["kappa"] = mejor
    json.dump(j, open(C.PARAMETROS, "w"))


if __name__ == "__main__":
    main()
