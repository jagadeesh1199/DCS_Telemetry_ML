import socket
import csv
import datetime
import os

# --- CONFIGURATION ---
UDP_IP = "127.0.0.1"
UDP_PORT = 55000
BUFFER_SIZE = 8192

# --- SETUP NETWORK ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.settimeout(1.0)

# --- SETUP FILE ---
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f"dcs_flight_data_normal_run{timestamp}.csv"

# Clear screen for dashboard view
os.system('cls' if os.name == 'nt' else 'clear')

print("-" * 60)
print(f"📡 DIGITAL TWIN RECEIVER ACTIVE")
print(f"👂 Listening on Port: {UDP_PORT}")
print(f"💾 Recording to:      {csv_filename}")
print("-" * 60)
print("Waiting for aircraft data stream...")

# 29 HEADERS (Must match Export.lua exactly)
headers = [
    "Time", "Alt_Radar", "VSI", "TAS", "Mach", "AoA", "SideSlip", "G_Load", 
    "Pitch", "Roll", "Yaw", 
    "RPM_L", "RPM_R", "Temp_L", "Temp_R", 
    "Gear", "Flaps", "Airbrake", "Hyd_Fail",
    "FuelFlow_L", "FuelFlow_R", 
    "Cannon_Shells", "Flares", "Chaff", "Master_Warn",
    "ACS_Active", "EOS_Active", "Fire_L", "Fire_R"
]

with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(headers)

    while True:
        try:
            # 1. Receive Packet
            data, addr = sock.recvfrom(BUFFER_SIZE)
            decoded_line = data.decode('utf-8').strip()
            values = decoded_line.split(',')
            
            # 2. Verify Data Integrity (Must be 29 items)
            if len(values) == 29:
                writer.writerow(values)
                
                # --- LIVE DASHBOARD ---
                # Parse key variables for display
                alt     = float(values[1])  # Radar Alt
                mach    = float(values[4])
                SideSlip = float(values[6])
                g_load  = float(values[7])
                rpm_l   = float(values[11])
                rpm_r   = float(values[12])
                ff_l    = float(values[19])
                ff_r    = float(values[20])
                shells  = int(values[21])
                fire_l  = int(values[27])
                fire_r  = int(values[28])
                
                # Calculate total fuel flow (kg/min)
                flow_rate = (ff_l + ff_r) * 60
                
                # Status Logic
                status = "🟢 SYSTEMS OK"
                if fire_l or fire_r:
                    status = "🔥🔥 ENGINE FIRE 🔥🔥"
                elif int(values[24]): # Master Warn
                    status = "⚠️ MASTER CAUTION"
                
                # Print Dashboard (Overwrites line)
                print(f"\r✈️  M{mach:.2f} | S: {SideSlip:.2f} | 📏 {alt:04.0f}m | G: {g_load:.1f} | ⛽ FLOW: {flow_rate:04.0f} kg/m | 🔫 AMMO: {shells:03d} | {status}", end="")
            
            else:
                # Debugging: If mismatch occurs, print it on a new line
                print(f"\n⚠️ Data Mismatch: Expected 29 columns, got {len(values)}")

        except socket.timeout:
            continue
        except KeyboardInterrupt:
            print(f"\n\n🛑 CAPTURE STOPPED. Data saved to {csv_filename}")
            break