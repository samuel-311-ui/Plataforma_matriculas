"""Genera parametros.json a partir de la telemetría medida (datos/telemetry_log.csv).

Toma solo la ventana de medición sin congestión (datos/calibracion_meta.json) y,
por tipo de solicitud, guarda las muestras (pre_ms, hold_ms) para remuestreo
(bootstrap): el simulador usa la distribución empírica, no una normal supuesta.
La fracción de CPU sale de datos/cpu_por_peticion.json (medir_cpu.py); si no
existe se asume que toda la petición consume CPU (cota pesimista).
"""
import json
import os

import pandas as pd

import config as C

TIPOS = {"consulta": ("GET", "/asignaturas"), "matricula": ("POST", "/matriculas")}


def main():
    meta = json.load(open(os.path.join(C.DATOS, "calibracion_meta.json")))
    d = pd.read_csv(os.path.join(C.DATOS, "telemetry_log.csv"))
    d = d[(d.timestamp >= meta["inicio_medicion"]) & (d.timestamp <= meta["fin_medicion"])]
    try:
        cpu = json.load(open(os.path.join(C.DATOS, "cpu_por_peticion.json")))
    except FileNotFoundError:
        cpu = None
    out = {"origen": "datos/telemetry_log.csv", "tipos": {}}
    for nombre, (m, ruta) in TIPOS.items():
        x = d[(d.method == m) & (d.endpoint == ruta) & (d.status_code < 300)]
        pre, hold = x.pre_ms.values / 1000, x.hold_ms.values / 1000
        cpu_total = (cpu[nombre]["cpu_ms"] / 1000) if cpu else (pre + hold).mean()
        cpu_hold = max(cpu_total - pre.mean(), 0.0)
        out["tipos"][nombre] = {
            "n": int(len(x)),
            "pre_s": [round(v, 6) for v in pre],
            "hold_s": [round(v, 6) for v in hold],
            "frac_cpu_hold": float(min(cpu_hold / hold.mean(), 1.0)),
            "media_pre_ms": float(pre.mean() * 1000),
            "media_hold_ms": float(hold.mean() * 1000),
            "cpu_total_ms": float(cpu_total * 1000),
            "total_p95_ms": float(x.duration_ms.quantile(.95)),
        }
        print(f"{nombre}: n={len(x)} pre={pre.mean()*1000:.2f} ms hold={hold.mean()*1000:.2f} ms "
              f"cpu={cpu_total*1000:.2f} ms frac_cpu_hold={out['tipos'][nombre]['frac_cpu_hold']:.2f}")
    out["kappa"] = C.KAPPA_DEFECTO
    json.dump(out, open(C.PARAMETROS, "w"))
    print("->", C.PARAMETROS)


if __name__ == "__main__":
    main()
