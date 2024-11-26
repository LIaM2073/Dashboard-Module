import tkinter as tk
from tkinter import ttk
import serial
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import os

# Initialize serial communication with the STM32 (adjust COM port and baudrate)
try:
    ser = serial.Serial('COM3', baudrate=9600, timeout=1)
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    ser = None

# Global data variables
pressure_data, accumulator_pressure_data, inlet_temp_data = [], [], []
thrust_data, time_data = [], []
log_data = []

# Constants for sensor scaling and normalization
PT_SCALE = 150  # Example scale: max pressure in psi
TEMP_SCALE = 260  # Max temperature in °C
THRUST_SCALE = 1000  # Example scale: max thrust in mN
VOLTAGE_RANGE = (0.5, 4.5)

# Function to normalize sensor data
def normalize_data(raw_voltage, scale, voltage_range=VOLTAGE_RANGE):
    min_v, max_v = voltage_range
    normalized = (raw_voltage - min_v) / (max_v - min_v)
    return normalized * scale

# Function to read data from STM32
def read_from_stm32():
    global pressure_data, accumulator_pressure_data, inlet_temp_data, thrust_data, time_data, log_data
    while True:
        try:
            if ser and ser.in_waiting > 0:
                data = ser.readline().decode('utf-8').strip()
                parts = data.split(',')
                if len(parts) == 4:
                    tank_voltage, acc_voltage, temp_voltage, thrust_voltage = map(float, parts)

                    current_time = time.time() - start_time
                    time_data.append(current_time)

                    # Normalize sensor data
                    tank_pressure = normalize_data(tank_voltage, PT_SCALE)
                    accumulator_pressure = normalize_data(acc_voltage, PT_SCALE)
                    inlet_temperature = normalize_data(temp_voltage, TEMP_SCALE)
                    thrust = normalize_data(thrust_voltage, THRUST_SCALE)

                    pressure_data.append(tank_pressure)
                    accumulator_pressure_data.append(accumulator_pressure)
                    inlet_temp_data.append(inlet_temperature)
                    thrust_data.append(thrust)

                    # Log data
                    log_data.append([current_time, tank_pressure, accumulator_pressure, inlet_temperature, thrust])
                    
                    # Update GUI
                    pressure_label.config(text=f"Tank Pressure: {tank_pressure:.2f} psi")
                    acc_pressure_label.config(text=f"Accumulator Pressure: {accumulator_pressure:.2f} psi")
                    inlet_temp_label.config(text=f"Inlet Temperature: {inlet_temperature:.2f} °C")
                    thrust_label.config(text=f"Thrust: {thrust:.2f} mN")
        except Exception as e:
            print(f"Error reading from serial: {e}")
        time.sleep(0.1)

# Function to save logged data to a USB drive
def save_log():
    if log_data:
        df = pd.DataFrame(log_data, columns=["Time (s)", "Tank Pressure (psi)", "Accumulator Pressure (psi)", 
                                             "Inlet Temperature (°C)", "Thrust (mN)"])
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        drive_letter = 'E:'  # Update with correct USB drive letter
        if os.path.exists(drive_letter):
            file_path = os.path.join(drive_letter, f"dashboard_log_{timestamp}.csv")
            df.to_csv(file_path, index=False)
            save_status_label.config(text=f"Log saved to {file_path}")
        else:
            save_status_label.config(text="USB drive not found. Save failed.")
    else:
        save_status_label.config(text="No data to save.")

# Real-time graph update function
def update_graph():
    global time_data, pressure_data, accumulator_pressure_data, inlet_temp_data, thrust_data

    ax1.clear()
    ax2.clear()
    ax3.clear()
    ax4.clear()

    ax1.plot(time_data, pressure_data, label='Tank Pressure (psi)', color='b')
    ax2.plot(time_data, accumulator_pressure_data, label='Accumulator Pressure (psi)', color='g')
    ax3.plot(time_data, inlet_temp_data, label='Inlet Temperature (°C)', color='r')
    ax4.plot(time_data, thrust_data, label='Thrust (mN)', color='c')

    for ax, ylabel in zip([ax1, ax2, ax3, ax4],
                          ['Tank Pressure (psi)', 'Accumulator Pressure (psi)', 'Inlet Temperature (°C)', 'Thrust (mN)']):
        ax.set_ylabel(ylabel)
        ax.legend(loc='upper left')

    ax4.set_xlabel('Time (s)')
    plt.tight_layout()
    canvas.draw()
    root.after(100, update_graph)

# GUI Setup
root = tk.Tk()
root.title("GSE Dashboard")
root.geometry("1000x800")

frame = ttk.Frame(root)
frame.pack(pady=10)

pressure_label = tk.Label(frame, text="Tank Pressure: N/A", font=("Helvetica", 16))
pressure_label.grid(row=0, column=0, padx=10, pady=5)
acc_pressure_label = tk.Label(frame, text="Accumulator Pressure: N/A", font=("Helvetica", 16))
acc_pressure_label.grid(row=0, column=1, padx=10, pady=5)
inlet_temp_label = tk.Label(frame, text="Inlet Temperature: N/A", font=("Helvetica", 16))
inlet_temp_label.grid(row=1, column=0, padx=10, pady=5)
thrust_label = tk.Label(frame, text="Thrust: N/A", font=("Helvetica", 16))
thrust_label.grid(row=1, column=1, padx=10, pady=5)

save_button = tk.Button(frame, text="Save Log", command=save_log, font=("Helvetica", 14))
save_button.grid(row=2, column=0, padx=10, pady=10)
save_status_label = tk.Label(frame, text="", font=("Helvetica", 12))
save_status_label.grid(row=2, column=1, columnspan=2, pady=5)

fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(10, 10))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(pady=20)

# Start the threads
start_time = time.time()
if ser:
    thread = threading.Thread(target=read_from_stm32)
    thread.daemon = True
    thread.start()
else:
    print("Serial port not initialized.")

update_graph()
root.mainloop()
