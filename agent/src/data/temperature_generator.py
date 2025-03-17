import csv
import random

# Generate 200 random temperature values between 23 and 27
temperatures = [round(random.uniform(23, 27), 2) for _ in range(200)]

# Save the temperatures to a CSV file
with open("temp.csv", mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["temperature"])  # Write the header
    writer.writerows([[temp] for temp in temperatures])  # Write the data

print("Temperatures saved to temperatures.csv")