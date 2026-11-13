"""Utilidades compartidas: lectura de resultados, IC95 % (t de Student), Erlang C."""
import math
import os

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(RAIZ, "simulacion", "resultados")
FIG = os.path.join(RAIZ, "docs", "figuras")


def leer(nombre):
    return pd.read_csv(os.path.join(RES, f"{nombre}.csv"))


def ic95(x):
    """Media e intervalo de confianza del 95 % (t de Student) sobre las réplicas."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    m = x.mean()
    h = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    return m, h


def resumir(df, por, cols):
    """Tabla con media y semiancho IC95 de cada columna, agrupada por 'por'."""
    filas = []
    for k, g in df.groupby(por, dropna=False):
        k = k if isinstance(k, tuple) else (k,)
        fila = dict(zip(por, k)); fila["n_replicas"] = len(g)
        for c in cols:
            m, h = ic95(g[c]); fila[c] = m; fila[c + "_ic"] = h
        filas.append(fila)
    return pd.DataFrame(filas)


def erlang_c(lam, mu, c):
    """M/M/c: devuelve P_w, Lq, Wq, W, L, rho."""
    a = lam / mu
    rho = a / c
    s = sum(a ** k / math.factorial(k) for k in range(c))
    t = a ** c / (math.factorial(c) * (1 - rho))
    pw = t / (s + t)
    lq = pw * rho / (1 - rho)
    wq = lq / lam
    w = wq + 1 / mu
    return {"rho": rho, "P_espera": pw, "Lq": lq, "Wq": wq, "W": w, "L": lam * w}
