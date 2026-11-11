import simpy
import random
import numpy as np
import pandas as pd
import os
from config import (
    SIM_TIME, POOL_SIZE_BASE, POOL_SIZE_ALT, MAX_CONNECTIONS, 
    VAL_TIME_MEAN, VAL_TIME_STD, NUM_REPLICAS, LAMBDA_PICO
)

class PlataformaMatricula:
    def __init__(self, env, pool_size, max_queue):
        self.env = env
        self.servidores = simpy.Resource(env, capacity=pool_size)
        self.max_queue = max_queue
        self.cola_actual = 0
        self.abandonos = 0
        self.atendidos = 0
        self.tiempos_espera = []
        self.tiempos_sistema = []

def estudiante_process(env, id_est, plataforma):
    llegada = env.now
    
    # Límite duro, rechazo si la cola excede MAX_CONNECTIONS
    if plataforma.cola_actual >= plataforma.max_queue:
        plataforma.abandonos += 1
        return
        
    plataforma.cola_actual += 1
    with plataforma.servidores.request() as req:
        # Regla C7: Abandono por timeout si espera más de 5 segundos
        results = yield req | env.timeout(5.0)
        
        plataforma.cola_actual -= 1
        if req in results:
            inicio_servicio = env.now
            espera = inicio_servicio - llegada
            plataforma.tiempos_espera.append(espera)
            
            # Tiempo de servicio lognormal calibrado
            tiempo_servicio = random.lognormvariate(np.log(VAL_TIME_MEAN), VAL_TIME_STD)
            yield env.timeout(tiempo_servicio)
            
            tiempo_total = env.now - llegada
            plataforma.tiempos_sistema.append(tiempo_total)
            plataforma.atendidos += 1
        else:
            plataforma.abandonos += 1

def generador_llegadas(env, plataforma, tasa_llegada):
    id_est = 0
    while True:
        t_entre_llegadas = random.expovariate(tasa_llegada)
        yield env.timeout(t_entre_llegadas)
        id_est += 1
        env.process(estudiante_process(env, id_est, plataforma))

def ejecutar_simulacion(seed, pool_size):
    random.seed(seed)
    np.random.seed(seed)
    env = simpy.Environment()
    plataforma = PlataformaMatricula(env, pool_size=pool_size, max_queue=MAX_CONNECTIONS)
    
    env.process(generador_llegadas(env, plataforma, tasa_llegada=LAMBDA_PICO))
    env.run(until=SIM_TIME * 60)
    
    total_solicitudes = plataforma.atendidos + plataforma.abandonos
    tasa_abandono = (plataforma.abandonos / total_solicitudes * 100) if total_solicitudes > 0 else 0
    espera_media = np.mean(plataforma.tiempos_espera) if plataforma.tiempos_espera else 0
    sistema_medio = np.mean(plataforma.tiempos_sistema) if plataforma.tiempos_sistema else 0
    p95_latencia = np.percentile(plataforma.tiempos_sistema, 95) if plataforma.tiempos_sistema else 0
    
    return {
        "atendidos": plataforma.atendidos,
        "abandonos": plataforma.abandonos,
        "tasa_abandono": tasa_abandono,
        "espera_media_Wq": espera_media,
        "sistema_medio_W": sistema_medio,
        "p95_latencia": p95_latencia
    }

if __name__ == "__main__":
    os.makedirs("resultados", exist_ok=True)
    
    print(f"Ejecutando {NUM_REPLICAS} réplicas del Escenario Base (Pool = {POOL_SIZE_BASE})...")
    res_base = [ejecutar_simulacion(seed=42 + i, pool_size=POOL_SIZE_BASE) for i in range(NUM_REPLICAS)]
    df_base = pd.DataFrame(res_base)
    df_base.to_csv("resultados/resultados_base.csv", index=False)
    
    print(f"Ejecutando {NUM_REPLICAS} réplicas del Escenario Alternativo (Pool = {POOL_SIZE_ALT})...")
    res_alt = [ejecutar_simulacion(seed=42 + i, pool_size=POOL_SIZE_ALT) for i in range(NUM_REPLICAS)]
    df_alt = pd.DataFrame(res_alt)
    df_alt.to_csv("resultados/resultados_alt.csv", index=False)
    
    print("Simulación finalizada:  Archivos creados en simulacion/resultados/")