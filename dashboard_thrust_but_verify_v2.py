import tkinter as tk
from tkinter import ttk
import serial
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

# Install pySerial and matplotlib if not already installed:
# pip install pyserial matplotlib pandas

# Initialize serial communication with the STM32 (adjust COM port and baudrate)
try:
    ser = serial.Serial('COM3', baudrate=9600, timeout=1)
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    ser = None

# Global lists to store real-time data for plotting
pressure_data = []
accumulator_pressure_data = []
inlet_temp_data = []
mass_flow_data = []
thrust_data = []
time_data = []

# Data logging
log_columns = ['Time (s)', 'Tank Pressure (psi)', 'Accumulator Pressure (psi)',
              'Inlet Temperature (°C)', 'Mass Flow Rate (g/s)', 'Thrust (mN)']
log_data = []

# Function to read data from STM32
def read_from_stm32():
    global pressure_data, accumulator_pressure_data, inlet_temp_data, mass_flow_data, thrust_data, time_data, log_data
    while True:
        try:
            if ser and ser.in_waiting > 0:
                data = ser.readline().decode('utf-8').strip()
                # Expected data format: pressure,acc_pressure,inlet_temp,mass_flow,thrust
                parts = data.split(',')
                if len(parts) == 5:
                    tank_pressure, acc_pressure, inlet_temp, mass_flow, thrust = map(float, parts)
                    
                    current_time = time.time() - start_time
                    time_data.append(current_time)
                    pressure_data.append(tank_pressure)
                    accumulator_pressure_data.append(acc_pressure)
                    inlet_temp_data.append(inlet_temp)
                    mass_flow_data.append(mass_flow)
                    thrust_data.append(thrust)
                    
                    # Update labels on the GUI
                    pressure_label.config(text=f"Tank Pressure: {tank_pressure:.2f} psi")
                    acc_pressure_label.config(text=f"Accumulator Pressure: {acc_pressure:.2f} psi")
                    inlet_temp_label.config(text=f"Inlet Temperature: {inlet_temp:.2f} °C")
                    mass_flow_label.config(text=f"Mass Flow Rate: {mass_flow:.3f} g/s")
                    thrust_label.config(text=f"Thrust: {thrust:.2f} mN")
                    
                    # Log the data
                    log_data.append([current_time, tank_pressure, acc_pressure, inlet_temp, mass_flow, thrust])
        except ValueError:
            # Handle the case where conversion to float fails
            print(f"Invalid data received: {data}")
        except Exception as e:
            print(f"Error reading from serial: {e}")
        time.sleep(0.5)

# Function to send command to STM32
def send_command():
    command = command_entry.get()
    if ser:
        try:
            ser.write((command + '\n').encode('utf-8'))
            status_label.config(text=f"Sent: {command}")
        except serial.SerialException as e:
            status_label.config(text=f"Error: {e}")
    else:
        status_label.config(text="Serial port not open")

# Function to update the real-time graph
def update_graph():
    global time_data, pressure_data, accumulator_pressure_data, inlet_temp_data, mass_flow_data, thrust_data
    
    # Clear previous plots
    ax1.clear()
    ax2.clear()
    ax3.clear()
    ax4.clear()
    ax5.clear()

    # Plot pressure over time
    ax1.plot(time_data, pressure_data, label='Tank Pressure (psi)', color='b')
    ax1.set_ylabel('Tank Pressure (psi)')
    ax1.legend(loc='upper left')
    
    # Plot accumulator pressure over time
    ax2.plot(time_data, accumulator_pressure_data, label='Accumulator Pressure (psi)', color='g')
    ax2.set_ylabel('Accumulator Pressure (psi)')
    ax2.legend(loc='upper left')
    
    # Plot inlet temperature over time
    ax3.plot(time_data, inlet_temp_data, label='Inlet Temperature (°C)', color='r')
    ax3.set_ylabel('Inlet Temperature (°C)')
    ax3.legend(loc='upper left')
    
    # Plot mass flow rate over time
    ax4.plot(time_data, mass_flow_data, label='Mass Flow Rate (g/s)', color='m')
    ax4.set_ylabel('Mass Flow Rate (g/s)')
    ax4.legend(loc='upper left')
    
    # Plot thrust over time
    ax5.plot(time_data, thrust_data, label='Thrust (mN)', color='c')
    ax5.set_ylabel('Thrust (mN)')
    ax5.set_xlabel('Time (s)')
    ax5.legend(loc='upper left')
    
    # Adjust layout
    plt.tight_layout()
    
    # Draw the updated plot
    canvas.draw()
    
    # Schedule next update
    root.after(1000, update_graph)

# Function to save logged data to CSV
def save_log():
    if log_data:
        df = pd.DataFrame(log_data, columns=log_columns)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"dashboard_log_{timestamp}.csv"
        df.to_csv(filename, index=False)
        save_status_label.config(text=f"Log saved to {filename}")
    else:
        save_status_label.config(text="No data to save")

# Setup Tkinter GUI
root = tk.Tk()
root.title("GSE Dashboard")
root.geometry("1000x800")

# Create a frame for sensor data display
frame = ttk.Frame(root)
frame.pack(pady=10)

# Labels to display real-time sensor data
pressure_label = tk.Label(frame, text="Tank Pressure: N/A", font=("Helvetica", 16))
pressure_label.grid(row=0, column=0, padx=10, pady=5)

acc_pressure_label = tk.Label(frame, text="Accumulator Pressure: N/A", font=("Helvetica", 16))
acc_pressure_label.grid(row=0, column=1, padx=10, pady=5)

inlet_temp_label = tk.Label(frame, text="Inlet Temperature: N/A", font=("Helvetica", 16))
inlet_temp_label.grid(row=1, column=0, padx=10, pady=5)

mass_flow_label = tk.Label(frame, text="Mass Flow Rate: N/A", font=("Helvetica", 16))
mass_flow_label.grid(row=1, column=1, padx=10, pady=5)

thrust_label = tk.Label(frame, text="Thrust: N/A", font=("Helvetica", 16))
thrust_label.grid(row=2, column=0, padx=10, pady=5)

# Command Entry to send commands to STM32
command_label = tk.Label(frame, text="Send Command:", font=("Helvetica", 14))
command_label.grid(row=3, column=0, padx=10, pady=10)

command_entry = tk.Entry(frame, width=30, font=("Helvetica", 14))
command_entry.grid(row=3, column=1, padx=10, pady=10)

send_button = tk.Button(frame, text="Send", command=send_command, font=("Helvetica", 14))
send_button.grid(row=3, column=2, padx=10, pady=10)

# Label to display status of command sent
status_label = tk.Label(frame, text="Status: N/A", font=("Helvetica", 12))
status_label.grid(row=4, column=0, columnspan=3, pady=5)

# Button to save log
save_button = tk.Button(frame, text="Save Log", command=save_log, font=("Helvetica", 14))
save_button.grid(row=5, column=0, padx=10, pady=10)

# Label to display save status
save_status_label = tk.Label(frame, text="", font=("Helvetica", 12))
save_status_label.grid(row=5, column=1, columnspan=2, pady=5)

# Set up matplotlib figure for real-time plotting
fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(10, 15))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(pady=20)

# Start reading data from STM32
start_time = time.time()
if ser:
    thread = threading.Thread(target=read_from_stm32)
    thread.daemon = True
    thread.start()
else:
    print("Serial port not initialized.")

# Start updating the real-time graph
update_graph()

# Start the Tkinter main loop
root.mainloop()
