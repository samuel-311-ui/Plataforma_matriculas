"""Tablas resumen (media ± IC95 %, 30 réplicas) en Markdown -> simulacion/resultados/tablas.md.
    python analisis/tablas.py
"""
import os

import pandas as pd

from comun import RES, leer, resumir

COLS = ["p95_s", "p99_s", "abandono", "util_cpu_pico", "util_pool_pico", "err_little"]


def fmt(df, cols, extra):
    out = []
    for _, r in df.iterrows():
        fila = [str(int(r[e])) if isinstance(r[e], float) and float(r[e]).is_integer() else str(r[e]) for e in extra]
        for c in cols:
            esc = 100 if c in ("abandono", "util_cpu_pico", "util_pool_pico") else 1
            nd = 2 if esc == 100 else 3
            if c == "err_little":
                fila.append(f"{100 * r[c]:.1e} %")
            else:
                fila.append(f"{esc * r[c]:.{nd}f} ± {esc * r[c + '_ic']:.{nd}f}")
        out.append("| " + " | ".join(fila) + " |")
    return out


def tabla(nombre, por, extra, titulo):
    d = leer(nombre)
    r = resumir(d, por, COLS)
    cab = extra + ["p95 (s)", "p99 (s)", "abandono (%)", "util CPU pico (%)", "util pool pico (%)", "err. Little"]
    t = [f"### {titulo}", "", "| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    t += fmt(r, COLS, por)
    return "\n".join(t) + "\n"


def main():
    partes = [
        tabla("e1_base", ["mundo"], ["mundo"], "Línea base de la Entrega 1 (N=3000, 1 réplica, pool 10)"),
        tabla("sens_N_e1", ["N"], ["N"], "Sensibilidad a la demanda, supuestos E1"),
        tabla("malla_e1", ["replicas", "pool"], ["réplicas", "pool"], "Malla réplicas × pool, N=6000, supuestos E1"),
        tabla("huerfanas_e1", ["huerfanas"], ["huérfanas"], "Trabajo huérfano, N=6000"),
        tabla("sens_N_medido", ["N"], ["N"], "Sensibilidad a la demanda, tiempos medidos"),
    ]
    d = leer("malla_medido")
    r = resumir(d, ["rps", "replicas", "pool"], ["p95_ms", "p99_ms", "ok"])
    t = ["### Malla con tiempos medidos (lazo abierto, T=10 s)", "",
         "| req/s | réplicas | pool | p95 (ms) | p99 (ms) | peticiones OK (%) |", "|---|---|---|---|---|---|"]
    for _, x in r.iterrows():
        t.append(f"| {int(x.rps)} | {int(x.replicas)} | {int(x.pool)} | {x.p95_ms:.1f} ± {x.p95_ms_ic:.1f} | "
                 f"{x.p99_ms:.1f} ± {x.p99_ms_ic:.1f} | {100*x.ok:.2f} ± {100*x.ok_ic:.2f} |")
    partes.append("\n".join(t) + "\n")
    s = "\n".join(partes)
    open(os.path.join(RES, "tablas.md"), "w").write(s)
    print(s)


if __name__ == "__main__":
    main()
