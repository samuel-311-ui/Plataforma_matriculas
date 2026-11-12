"""Modelo de simulación de eventos discretos (SimPy) de la plataforma de matrículas.

Estructura (igual a la API real medida):
  llegada -> [cola de hilos] -> etapa 1+2: validación/enrutamiento (CPU, GIL)
          -> [cola del pool, timeout POOL_TIMEOUT] -> etapa 3: conexión retenida
             (parte de CPU en Python + parte de espera a PostgreSQL)
Por réplica de la API hay: HILOS hilos, 1 CPU efectiva (el GIL serializa el código
Python) y un pool de P conexiones. El balanceador reparte en round-robin.

Tiempos de servicio: remuestreo de la telemetría real (parametros.json).
La CPU se infla por el factor kappa (contención de GIL/cambios de contexto), que se
ajusta contra el sistema real en ajustar_kappa.py.

Cliente (Entrega 1): timeout T, hasta k reintentos con pausa exponencial; si agota
los reintentos el estudiante abandona (C7).
"""
import json
import math
import random

import numpy as np
import simpy

import config as C


def cargar_parametros(ruta=C.PARAMETROS):
    p = json.load(open(ruta))
    for t in p["tipos"].values():
        t["pre"] = np.array(t["pre_s"])
        t["hold"] = np.array(t["hold_s"])
    return p


def parametros_e1(params, media_consulta=0.15, media_matricula=0.40, n=20000):
    """Supuestos de servicio de la Entrega 1: toda la solicitud ocupa la conexión del pool
    un tiempo exponencial (0.15 s consulta, 0.40 s matrícula), sin CPU de Python limitante."""
    rng = np.random.default_rng(2026)
    q = {"kappa": 1.0, "tipos": {}}
    for nombre, m in (("consulta", media_consulta), ("matricula", media_matricula)):
        q["tipos"][nombre] = {"pre": np.zeros(n), "hold": rng.exponential(m, n), "frac_cpu_hold": 0.0}
    return q


class Replica:
    def __init__(self, env, pool, hilos, bins):
        self.env = env
        self.hilos = simpy.Resource(env, hilos)
        self.cpu = simpy.Resource(env, 1)
        self.pool = simpy.Resource(env, pool)
        self.cpu_bin = np.zeros(bins)
        self.pool_bin = np.zeros(bins)
        self.cpu_total = 0.0
        self.pool_total = 0.0
        self.cpu_t = 0.0


class Sistema:
    def __init__(self, params, replicas=1, pool=C.POOL_SIZE_BASE, hilos=C.HILOS_POR_REPLICA,
                 kappa=None, pool_timeout=C.POOL_TIMEOUT, huerfanas=True, semilla=1,
                 horizonte=C.HORIZONTE):
        self.env = simpy.Environment()
        self.p = params
        self.kappa = params["kappa"] if kappa is None else kappa
        self.pool_timeout = pool_timeout
        self.huerfanas = huerfanas
        self.rnd = random.Random(semilla)
        self.nbins = int(horizonte // 60) + 60
        self.reps = [Replica(self.env, pool, hilos, self.nbins) for _ in range(replicas)]
        self.rr = 0
        # Little (por intento en el servidor)
        self.n_sis = 0
        self.area = 0.0
        self.t_ult = 0.0
        self.sum_w = 0.0
        self.n_llegadas = 0
        self.n_term = 0
        self.t_primera = None
        self.intentos = []        # (t_llegada, tipo, ok, latencia_cliente)
        self.esperas = []         # (t_llegada, espera_pool_s) por intento atendido

    # ------------------------------------------------------------ servidor
    def _cambia(self, d):
        t = self.env.now
        self.area += self.n_sis * (t - self.t_ult)
        self.t_ult = t
        self.n_sis += d

    def _muestra(self, tipo):
        t = self.p["tipos"][tipo]
        i = self.rnd.randrange(len(t["pre"]))
        return t["pre"][i], t["hold"][i], t["frac_cpu_hold"]

    def _cpu(self, rep, dur):
        with rep.cpu.request() as r:
            yield r
            d = dur * self.kappa
            b = min(int(self.env.now // 60), self.nbins - 1)
            rep.cpu_bin[b] += d
            rep.cpu_total += d
            yield self.env.timeout(d)

    def atender(self, rep, tipo, cancelado):
        """Procesa un intento en el servidor. Devuelve 200 o 500 (pool agotado)."""
        env = self.env
        t_ent = env.now
        self.n_llegadas += 1
        self._cambia(+1)
        estado = 200
        try:
            pre, hold, f = self._muestra(tipo)
            with rep.hilos.request() as h:
                yield h
                if cancelado["x"] and not self.huerfanas:
                    return 499
                yield env.process(self._cpu(rep, pre))
                if cancelado["x"] and not self.huerfanas:
                    return 499
                with rep.pool.request() as c:
                    t_cola = env.now
                    res = yield c | env.timeout(self.pool_timeout)
                    self.esperas.append((t_ent, env.now - t_cola))
                    if c not in res:
                        estado = 500
                        return 500
                    t0 = env.now
                    yield env.process(self._cpu(rep, hold * f))
                    yield env.timeout(hold * (1 - f))
                    d = env.now - t0
                    rep.pool_total += d
                    b = min(int(env.now // 60), self.nbins - 1)
                    rep.pool_bin[b] += d
            return 200
        finally:
            self._cambia(-1)
            self.n_term += 1
            self.sum_w += env.now - t_ent

    def _elegir(self):
        r = self.reps[self.rr % len(self.reps)]
        self.rr += 1
        return r

    # -------------------------------------------------------------- cliente
    def intento(self, tipo, timeout):
        """Un intento HTTP. Devuelve (ok, latencia) tal como la ve el cliente."""
        env = self.env
        t0 = env.now
        cancel = {"x": False}
        proc = env.process(self.atender(self._elegir(), tipo, cancel))
        res = yield proc | env.timeout(timeout)
        if proc in res:
            ok = proc.value == 200
            lat = env.now - t0
        else:
            cancel["x"] = True
            ok, lat = False, timeout
        self.intentos.append((t0, tipo, ok, lat))
        return ok, lat

    def paso(self, tipo, T, k, pausa):
        """Un paso del estudiante con reintentos. Devuelve (ok, tiempo_total)."""
        t0 = self.env.now
        for i in range(k + 1):
            ok, _ = yield self.env.process(self.intento(tipo, T))
            if ok:
                return True, self.env.now - t0
            if i < k:
                yield self.env.timeout(self.rnd.expovariate(1.0 / pausa))
        return False, self.env.now - t0

    def estudiante(self, t_llegada, res, T, k, pausa):
        yield self.env.timeout(t_llegada)
        ok, t1 = yield self.env.process(self.paso("consulta", T, k, pausa))
        res["pasos"].append(("consulta", ok, t1))
        if not ok:
            res["abandonos"] += 1
            return
        mu = math.log(C.ESPERA_CONSULTA_MEDIA) - 0.5 * math.log(1 + C.ESPERA_CONSULTA_CV ** 2)
        sg = math.sqrt(math.log(1 + C.ESPERA_CONSULTA_CV ** 2))
        yield self.env.timeout(self.rnd.lognormvariate(mu, sg))
        if self.rnd.random() < C.P_MATRICULA:
            ok, t2 = yield self.env.process(self.paso("matricula", T, k, pausa))
            res["pasos"].append(("matricula", ok, t2))
            if not ok:
                res["abandonos"] += 1
                return
        res["completados"] += 1

    # ------------------------------------------------------------ escenarios
    def tiempos_llegada(self, n, perfil="pico60"):
        """Perfiles de llegada de la Entrega 1 (las tablas 6 y 8 no coinciden entre sí):
        pico60: 40 % en el primer minuto, 60 % restante exp(tau)   (tabla 6, lambda=32 req/s con N=3000)
        tabla8: 70 % U[0,600] s y 30 % exp(tau)                    (tabla 8)"""
        out = []
        for _ in range(n):
            u = self.rnd.random()
            if perfil == "pico60":
                t = self.rnd.uniform(0, 60.0) if u < 0.40 else self.rnd.expovariate(1.0 / C.TAU_COLA)
            else:
                t = self.rnd.uniform(0, C.VENTANA_PICO) if u < C.FRAC_PICO else self.rnd.expovariate(1.0 / C.TAU_COLA)
            while t > C.HORIZONTE:             # solo llegadas dentro del horizonte de 2 h
                t = self.rnd.expovariate(1.0 / C.TAU_COLA)
            out.append(t)
        return out

    def correr_estudiantes(self, n, T=C.T_CLIENTE, k=C.K_REINTENTOS, pausa=C.PAUSA_REINTENTO_MEDIA,
                           perfil="pico60"):
        res = {"pasos": [], "abandonos": 0, "completados": 0}
        for ta in self.tiempos_llegada(n, perfil):
            self.env.process(self.estudiante(ta, res, T, k, pausa))
        self.env.run()          # hasta vaciar el sistema (Little exacto)
        return self.metricas(res, n)

    def correr_abierto(self, rps, seg, timeout=15.0, p_mat=0.375, calentamiento=0.0, hasta=None):
        """Carga de llegadas Poisson sin reintentos (para validar contra el sistema real)."""
        env = self.env

        def gen():
            t = 0.0
            while t < seg:
                t += self.rnd.expovariate(rps)
                yield env.timeout(max(t - env.now, 0))
                tipo = "matricula" if self.rnd.random() < p_mat else "consulta"
                env.process(self.intento(tipo, timeout))
        snap = {}

        def foto():
            yield env.timeout(calentamiento)
            self._cambia(0)
            snap["area"], snap["t"] = self.area, env.now
        env.process(gen())
        env.process(foto())
        if hasta is None:
            env.run()
        else:
            env.run(until=hasta)
        a = np.array([(x[0], x[2], x[3]) for x in self.intentos if x[0] >= calentamiento])
        ok = a[:, 1] == 1
        lat = a[ok, 2]
        out = {"n": len(a), "ok": float(ok.mean()),
               "media_ms": float(lat.mean() * 1000) if len(lat) else float("nan"),
               "p95_ms": float(np.percentile(lat, 95) * 1000) if len(lat) else float("nan"),
               "p99_ms": float(np.percentile(lat, 99) * 1000) if len(lat) else float("nan")}
        e = np.array([x[1] for x in self.esperas if x[0] >= calentamiento])
        if len(e):
            self._cambia(0)
            out.update({"P_espera": float((e > 1e-9).mean()), "Wq": float(e.mean()),
                        "W": float(lat.mean()) if len(lat) else float("nan"),
                        "L": (self.area - snap["area"]) / (env.now - snap["t"]),
                        "lambda": len(a) / (env.now - snap["t"]) if hasta else len(a) / (seg - calentamiento)})
        return out

    # -------------------------------------------------------------- métricas
    def metricas(self, res, n):
        self._cambia(0)
        T = self.t_ult
        Tu = min(T, C.HORIZONTE)             # utilización sobre el horizonte de 2 h
        lat = np.array([x[3] for x in self.intentos if x[2]])
        nreq = len(self.intentos)
        cpu_u = np.mean([r.cpu_total for r in self.reps]) / Tu
        pool_u = np.mean([r.pool_total / (r.pool.capacity * Tu) for r in self.reps])
        # utilización en el minuto más cargado (pico)
        cpu_pico = max(r.cpu_bin.max() for r in self.reps) / 60.0
        pool_pico = max(r.pool_bin.max() / (r.pool.capacity * 60.0) for r in self.reps)
        lam = self.n_llegadas / T
        W = self.sum_w / max(self.n_term, 1)
        L = self.area / T
        pasos = res["pasos"]
        tp = np.array([x[2] for x in pasos if x[1]])
        return {
            "n_estudiantes": n,
            "abandono": res["abandonos"] / n,
            "completados": res["completados"] / n,
            "n_intentos": nreq,
            "fallos_intento": 1 - len(lat) / max(nreq, 1),
            "p50_s": float(np.percentile(lat, 50)) if len(lat) else float("nan"),
            "p95_s": float(np.percentile(lat, 95)) if len(lat) else float("nan"),
            "p99_s": float(np.percentile(lat, 99)) if len(lat) else float("nan"),
            "media_s": float(lat.mean()) if len(lat) else float("nan"),
            "paso_p95_s": float(np.percentile(tp, 95)) if len(tp) else float("nan"),
            "util_cpu": float(cpu_u), "util_pool": float(pool_u),
            "util_cpu_pico": float(cpu_pico), "util_pool_pico": float(pool_pico),
            "lambda": lam, "W": W, "L_sim": L, "L_little": lam * W,
            "err_little": abs(L - lam * W) / max(L, 1e-12),
            "t_fin": T,
        }
