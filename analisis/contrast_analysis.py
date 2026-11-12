"""Contraste teórico M/M/c (Erlang C) vs SimPy y verificación explícita de la Ley de Little.

No hay números escritos a mano: todo se calcula a partir de simulacion/resultados/*.csv.
    python analisis/contrast_analysis.py
"""
import numpy as np
import pandas as pd

from comun import erlang_c, ic95, leer, RES
import os


def contraste_mmc():
    d = leer("mmc_e1")
    lam, mu, c = 32.0, 4.0, 10
    t = erlang_c(lam, mu, c)
    filas = []
    for clave, nombre in (("P_espera", "P(espera) = P_w"), ("Wq", "Wq (s)"), ("W", "W (s)"), ("L", "L (solicitudes)")):
        m, h = ic95(d[clave])
        teo = t[clave]
        filas.append({"métrica": nombre, "teórico M/M/10": teo, "SimPy (media)": m, "IC95 ±": h,
                      "error relativo %": 100 * (m - teo) / teo,
                      "teórico dentro del IC95": bool(abs(m - teo) <= h)})
    # Lq a partir de L y de la utilización (L - Lq = lambda/mu)
    lq = d["L"] - d["lambda"] / mu
    m, h = ic95(lq)
    filas.insert(2, {"métrica": "Lq (en cola)", "teórico M/M/10": t["Lq"], "SimPy (media)": m, "IC95 ±": h,
                     "error relativo %": 100 * (m - t["Lq"]) / t["Lq"],
                     "teórico dentro del IC95": bool(abs(m - t["Lq"]) <= h)})
    return pd.DataFrame(filas), t


def little():
    """L = lambda * W verificado dentro de cada réplica, en el sistema y en estado estacionario M/M/10."""
    d = leer("e1_base")
    filas = []
    for mundo, g in d.groupby("mundo"):
        L, lw = g["L_sim"], g["L_little"]
        filas.append({"experimento": f"E1 base N=3000 ({mundo})", "L simulado (media)": L.mean(),
                      "λ·W (media)": lw.mean(), "error relativo máx %": 100 * g["err_little"].max()})
    m = leer("mmc_e1")
    lw = m["lambda"] * m["W"]
    filas.append({"experimento": "M/M/10 estacionario (λ=32, μ=4)", "L simulado (media)": m["L"].mean(),
                  "λ·W (media)": lw.mean(),
                  "error relativo máx %": 100 * (abs(m["L"] - lw) / m["L"]).max()})
    return pd.DataFrame(filas)


def main():
    pd.set_option("display.width", 200)
    mmc, t = contraste_mmc()
    li = little()
    print("Contraste M/M/10 (λ=32 req/s, μ=4 req/s, c=10, ρ=%.2f)" % t["rho"])
    print(mmc.round(4).to_string(index=False))
    print("\nVerificación de la Ley de Little (L = λW)")
    print(li.round(4).to_string(index=False))
    mmc.to_csv(os.path.join(RES, "tabla_mmc.csv"), index=False)
    li.to_csv(os.path.join(RES, "tabla_little.csv"), index=False)


if __name__ == "__main__":
    main()
