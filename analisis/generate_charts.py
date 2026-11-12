"""Genera las figuras del informe en docs/figuras/ a partir de simulacion/resultados/*.csv.
    python analisis/generate_charts.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from comun import FIG, RES, erlang_c, leer, resumir

SLA_P95, SLA_AB = 2.0, 0.03
AZ, NA, RO, VE = "#1f5fa8", "#d98b1c", "#b3261e", "#2e7d32"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .25, "figure.dpi": 130})


def guardar(fig, nombre):
    os.makedirs(FIG, exist_ok=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, nombre), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("->", nombre)


def fig_validacion():
    v = pd.read_csv(os.path.join(RES, "validacion.csv"))
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for a, c, tit in ((ax[0], "media", "Latencia media (ms)"), (ax[1], "p95", "Latencia p95 (ms)")):
        for g, col, mk in (("ajuste", AZ, "o"), ("fuera_de_muestra", RO, "s")):
            x = v[v.grupo == g]
            a.scatter(x[f"{c}_real_ms"], x[f"{c}_sim_ms"], c=col, marker=mk, s=45,
                      label="ajuste (≤200 req/s)" if g == "ajuste" else "fuera de muestra (≥250 req/s)")
        lim = [5, v[[f"{c}_real_ms", f"{c}_sim_ms"]].max().max() * 1.5]
        a.plot(lim, lim, "k--", lw=1)
        a.set_xscale("log"); a.set_yscale("log")
        a.set_xlabel("sistema real"); a.set_ylabel("simulación"); a.set_title(tit)
    ax[0].legend(fontsize=8)
    fig.suptitle("Validación: simulador vs API real (1 réplica, Docker/local)", y=1.0)
    guardar(fig, "fig1_validacion.png")


def fig_mmc():
    d = leer("mmc_e1")
    t = erlang_c(32, 4, 10)
    cols = [("P_espera", "P(espera)"), ("Wq", "Wq (s)"), ("W", "W (s)"), ("L", "L")]
    fig, ax = plt.subplots(1, 4, figsize=(11, 3.2))
    for a, (c, n) in zip(ax, cols):
        m, h = d[c].mean(), 1.96 * d[c].std(ddof=1) / np.sqrt(len(d))
        a.bar(["M/M/10", "SimPy"], [t[c], m], color=[AZ, NA], yerr=[0, h], capsize=4)
        a.set_title(n)
    fig.suptitle("Contraste analítico (Erlang C) vs simulación, λ=32 req/s, μ=4 req/s, c=10", y=1.02)
    guardar(fig, "fig2_mmc.png")


def fig_sens_e1():
    r = resumir(leer("sens_N_e1"), ["N"], ["p95_s", "paso_p95_s", "abandono", "util_pool_pico"])
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    ax[0].errorbar(r.N, r.p95_s, r.p95_s_ic, marker="o", color=AZ, capsize=3)
    ax[0].axhline(SLA_P95, color=RO, ls="--", label="SLA p95 = 2 s"); ax[0].set_ylabel("p95 por intento (s)")
    ax[0].legend()
    ax[1].errorbar(r.N, 100 * r.abandono, 100 * r.abandono_ic, marker="o", color=NA, capsize=3)
    ax[1].axhline(100 * SLA_AB, color=RO, ls="--", label="límite 3 %"); ax[1].set_ylabel("abandono (%)")
    ax[1].legend()
    ax[2].errorbar(r.N, 100 * r.util_pool_pico, 100 * r.util_pool_pico_ic, marker="o", color=VE, capsize=3)
    ax[2].axhspan(70, 85, color=VE, alpha=.15, label="banda objetivo 70–85 %")
    ax[2].set_ylabel("utilización del pool, minuto pico (%)"); ax[2].legend()
    for a in ax: a.set_xlabel("estudiantes N")
    fig.suptitle("Política actual (1 réplica, pool 10), supuestos de la Entrega 1: sensibilidad a la demanda", y=1.02)
    guardar(fig, "fig3_sensibilidad_N_e1.png")


def fig_malla_e1():
    r = resumir(leer("malla_e1"), ["replicas", "pool"], ["p95_s", "abandono"])
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for a, c, tit, f in ((ax[0], "p95_s", "p95 por intento (s)", "{:.2f}"),
                         (ax[1], "abandono", "abandono (%)", "{:.1f}")):
        M = r.pivot(index="replicas", columns="pool", values=c)
        M = M * (100 if c == "abandono" else 1)
        im = a.imshow(M.values, cmap="RdYlGn_r", aspect="auto")
        a.set_xticks(range(len(M.columns)), M.columns); a.set_yticks(range(len(M.index)), M.index)
        a.set_xlabel("pool por réplica"); a.set_ylabel("réplicas de la API"); a.set_title(tit)
        a.grid(False)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                v = M.values[i, j]
                a.text(j, i, "—" if np.isnan(v) else f.format(v), ha="center", va="center", fontsize=9)
    fig.suptitle("Malla réplicas × pool, N=6000 (celdas '—' violan C6: réplicas×pool > 97)", y=1.02)
    guardar(fig, "fig4_malla_e1.png")


def fig_medido():
    r = resumir(leer("sens_N_medido"), ["N"], ["p95_s", "util_cpu_pico", "util_pool_pico", "abandono"])
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    ax[0].errorbar(r.N, 100 * r.util_cpu_pico, 100 * r.util_cpu_pico_ic, marker="o", color=RO, capsize=3, label="CPU (GIL)")
    ax[0].errorbar(r.N, 100 * r.util_pool_pico, 100 * r.util_pool_pico_ic, marker="s", color=AZ, capsize=3, label="pool")
    ax[0].axhspan(70, 85, color=VE, alpha=.15); ax[0].set_ylabel("utilización minuto pico (%)"); ax[0].legend()
    ax[1].errorbar(r.N, r.p95_s * 1000, r.p95_s_ic * 1000, marker="o", color=AZ, capsize=3)
    ax[1].set_yscale("log"); ax[1].set_ylabel("p95 por intento (ms)")
    ax[2].errorbar(r.N, 100 * r.abandono, 100 * r.abandono_ic, marker="o", color=NA, capsize=3)
    ax[2].set_ylabel("abandono (%)")
    for a in ax: a.set_xlabel("estudiantes N"); a.set_xscale("log")
    fig.suptitle("Sistema con tiempos de servicio medidos (1 réplica, pool 10): el cuello de botella es la CPU", y=1.02)
    guardar(fig, "fig5_sistema_medido.png")


def fig_malla_medido():
    d = leer("malla_medido")
    r = resumir(d, ["rps", "replicas", "pool"], ["p95_ms", "ok"])
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), sharey=False)
    for a, rps in zip(ax, sorted(r.rps.unique())):
        x = r[r.rps == rps]
        for p, mk in zip(sorted(x.pool.unique()), "osd"):
            y = x[x.pool == p].sort_values("replicas")
            a.errorbar(y.replicas, y.p95_ms, y.p95_ms_ic, marker=mk, capsize=3, label=f"pool {p}")
        a.set_yscale("log"); a.set_xlabel("réplicas de la API"); a.set_ylabel("p95 (ms)")
        a.set_xticks(sorted(x.replicas.unique())); a.set_title(f"{rps} req/s sostenidos"); a.legend()
    fig.suptitle("Sistema medido: más réplicas reduce la latencia; el tamaño del pool casi no importa", y=1.02)
    guardar(fig, "fig6_malla_medido.png")


def fig_huerfanas():
    r = resumir(leer("huerfanas_e1"), ["huerfanas"], ["abandono", "p95_s", "util_pool_pico"])
    fig, ax = plt.subplots(1, 2, figsize=(8, 3.4))
    etq = ["descarta (cancelación)" if not h else "completa (actual)" for h in r.huerfanas]
    ax[0].bar(etq, 100 * r.abandono, yerr=100 * r.abandono_ic, color=[NA, AZ], capsize=4); ax[0].set_ylabel("abandono (%)")
    ax[1].bar(etq, r.p95_s, yerr=r.p95_s_ic, color=[NA, AZ], capsize=4); ax[1].set_ylabel("p95 por intento (s)")
    fig.suptitle("Trabajo huérfano tras abandono del cliente (N=6000, pool 10)", y=1.02)
    guardar(fig, "fig7_huerfanas.png")


if __name__ == "__main__":
    for f in (fig_validacion, fig_mmc, fig_sens_e1, fig_malla_e1, fig_medido, fig_malla_medido, fig_huerfanas):
        try:
            f()
        except FileNotFoundError as e:
            print("omitida", f.__name__, "-", e.filename)
