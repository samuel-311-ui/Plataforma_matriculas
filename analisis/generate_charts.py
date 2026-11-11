import matplotlib.pyplot as plt
import pandas as pd
import os

# Crear carpeta de figuras si no existe
os.makedirs("../docs/figuras", exist_ok=True)

df_base = pd.read_csv("../simulacion/resultados/resultados_base.csv")
df_alt = pd.read_csv("../simulacion/resultados/resultados_alt.csv")

# --- Gráfica 1: Latencia p95 vs Umbral SLA ---
plt.figure(figsize=(8, 5))
plt.boxplot([df_base['p95_latencia'], df_alt['p95_latencia']], 
            tick_labels=['Política Actual (Pool=10)', 'Política Alt. (Pool=15)'])
plt.axhline(y=2.0, color='r', linestyle='--', linewidth=2, label='Umbral Máximo SLA (2.0s)')
plt.title('Latencia Percentil 95 (p95) por Escenario', fontsize=12, fontweight='bold')
plt.ylabel('Tiempo de Respuesta (segundos)')
plt.legend(loc='upper right')
plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.savefig('../docs/figuras/grafica_p95_sla.png', dpi=300)
plt.close()

# --- Gráfica 2: Tasa de Abandono por Política ---
plt.figure(figsize=(8, 5))
m_base = df_base['tasa_abandono'].mean()
m_alt = df_alt['tasa_abandono'].mean()

plt.bar(['Política Actual (Pool=10)', 'Política Alt. (Pool=15)'], [m_base, m_alt], color=['#d9534f', '#5cb85c'])
plt.axhline(y=3.0, color='r', linestyle='--', linewidth=2, label='Límite SLA Abandono (3.0%)')
plt.title('Porcentaje de Abandono y Rechazo por Política', fontsize=12, fontweight='bold')
plt.ylabel('Tasa de Abandono (%)')
plt.legend(loc='upper right')
plt.grid(axis='y', linestyle=':', alpha=0.6)
plt.tight_layout()
plt.savefig('../docs/figuras/grafica_abandonos.png', dpi=300)
plt.close()

print("Gráficas generadas exitosamente en docs/figuras/")