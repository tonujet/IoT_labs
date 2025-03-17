import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

num_rows = 150

x = np.linspace(-2.2 * np.pi,  np.pi, num_rows)
intensity = np.sin(x)

noise = np.random.normal(0, 0.02, num_rows)
intensity = np.clip(intensity + noise, 0, 1)

steps = list(range(len(intensity)))
df_to_save = pd.DataFrame({'intensity': intensity})
df_to_save.to_csv('rain.csv', index=False)

df_to_plot = pd.DataFrame({'Step': steps, 'Intensity': intensity})

plt.figure(figsize=(10, 6))
plt.plot(df_to_plot['Step'], df_to_plot['Intensity'], label='Rain Intensity', color='blue')
plt.title('Pseudo-random Rain Intensity for Car Sensor')
plt.xlabel('Steps')
plt.ylabel('Rain Intensity (0 to 1)')
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.show()
