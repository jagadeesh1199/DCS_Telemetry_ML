import socket
import csv
import datetime
import os

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
UDP_IP      = "127.0.0.1"
UDP_PORT    = 55000
BUFFER_SIZE = 8192

# ── HEADERS — 35 live columns, matches Export_Su25T_Clean.lua ─────────────────
HEADERS = [
    # DYNAMICS (7)
    "Time", "Alt_Radar", "VSI", "TAS", "Mach", "AoA", "G_Load",
    # ATTITUDE (3)
    "Pitch", "Roll", "Yaw",
    # PROPULSION (4)
    "RPM_L", "RPM_R", "Temp_L", "Temp_R",
    # SYSTEMS (3)
    "Hyd_Fail", "FuelFlow_L", "FuelFlow_R",
    # FLAGS (5)
    "Master_Warn", "ACS_Active", "EOS_Active", "Fire_L", "Fire_R",
    # WIND (3)
    "Wind_X", "Wind_Y", "Wind_Z",
    # ANGULAR RATES (3)
    "RollRate", "PitchRate", "YawRate",
    # VELOCITY VECTOR (3)
    "Vel_X", "Vel_Y", "Vel_Z",
    # FUEL + BARO (2)
    "Fuel_Internal", "Alt_Baro",
]

EXPECTED_COLS = len(HEADERS)  # 33
IDX = {h: i for i, h in enumerate(HEADERS)}

# ── NETWORK ───────────────────────────────────────────────────────────────────
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.settimeout(1.0)

# ── FILE ──────────────────────────────────────────────────────────────────────
timestamp    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"flight_data_{timestamp}.csv"

# ── STARTUP BANNER ────────────────────────────────────────────────────────────
os.system("cls" if os.name == "nt" else "clear")
print("-" * 65)
print("  DIGITAL TWIN RECEIVER — Su-25T Clean (33 cols)")
print(f"  Listening on port : {UDP_PORT}")
print(f"  Recording to      : {csv_filename}")
print(f"  Expecting columns : {EXPECTED_COLS}")
print("-" * 65)
print("  Waiting for aircraft data stream...")
print()

# ── HELPERS ───────────────────────────────────────────────────────────────────
def bar(value, lo, hi, width=10, fill="█", empty="░"):
    frac   = max(0.0, min(1.0, (value - lo) / (hi - lo) if hi != lo else 0))
    filled = round(frac * width)
    return fill * filled + empty * (width - filled)

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
with open(csv_filename, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(HEADERS)

    packet_count  = 0
    fault_packets = 0
    bad_packets   = 0

    while True:
        try:
            data, _ = sock.recvfrom(BUFFER_SIZE)
            decoded = data.decode("utf-8").strip()
            values  = decoded.split(",")

            # ── INTEGRITY CHECK ───────────────────────────────────────────────
            if len(values) != EXPECTED_COLS:
                bad_packets += 1
                if bad_packets <= 5:
                    print(
                        f"\n  [WARN] Expected {EXPECTED_COLS} cols, got {len(values)}"
                        f" — packet #{packet_count + 1}\n"
                    )
                continue

            # ── WRITE TO CSV ──────────────────────────────────────────────────
            writer.writerow(values)
            packet_count += 1
            if packet_count % 400 == 0:
                f.flush()

            # ── PARSE ─────────────────────────────────────────────────────────
            def fv(col):
                try:    return float(values[IDX[col]])
                except: return 0.0

            def iv(col):
                try:    return int(float(values[IDX[col]]))
                except: return 0

            t_val      = fv("Time")
            alt        = fv("Alt_Radar")
            vsi        = fv("VSI")
            mach       = fv("Mach")
            aoa        = fv("AoA")
            g_load     = fv("G_Load")
            pitch      = fv("Pitch")
            roll       = fv("Roll")
            rpm_l      = fv("RPM_L")
            rpm_r      = fv("RPM_R")
            temp_l     = fv("Temp_L")
            temp_r     = fv("Temp_R")
            ff_l       = fv("FuelFlow_L")
            ff_r       = fv("FuelFlow_R")
            roll_rate  = fv("RollRate")
            pitch_rate = fv("PitchRate")
            yaw_rate   = fv("YawRate")
            wind_x     = fv("Wind_X")
            wind_y     = fv("Wind_Y")
            wind_z     = fv("Wind_Z")
            fuel_int   = fv("Fuel_Internal")
            hyd        = iv("Hyd_Fail")
            mwarn      = iv("Master_Warn")
            acs        = iv("ACS_Active")
            eos        = iv("EOS_Active")
            fire_l     = iv("Fire_L")
            fire_r     = iv("Fire_R")

            flow_rate = (ff_l + ff_r) * 60  # kg/min

            any_fault = fire_l or fire_r or hyd
            if any_fault:
                fault_packets += 1

            # ── STATUS ────────────────────────────────────────────────────────
            if   fire_l and fire_r: status = "*** DUAL ENGINE FIRE  ***"
            elif fire_l:            status = "*** FIRE LEFT ENGINE  ***"
            elif fire_r:            status = "*** FIRE RIGHT ENGINE ***"
            elif hyd:               status = "*** HYD FAILURE       ***"
            elif mwarn:             status = "*** MASTER CAUTION    ***"
            elif acs:               status = "  ACS ACTIVE"
            elif eos:               status = "  EOS ACTIVE"
            elif rpm_l < 50:        status = "<<< RPM-L LOW"
            elif rpm_r < 50:        status = "<<< RPM-R LOW"
            else:                   status = "SYSTEMS OK"

            # ── LIVE DASHBOARD (4-line overwriting block) ─────────────────────
            LINES = 4
            dash = (
                # Line 1 — Flight state
                f"  T:{t_val:>7.1f}s | "
                f"Alt:{alt:>6.0f}m | "
                f"VSI:{vsi:>+6.1f} | "
                f"M:{mach:.3f} | "
                f"AoA:{aoa:>+5.1f}° | "
                f"G:{g_load:>+4.1f} | "
                f"Pitch:{pitch:>+5.1f}° Roll:{roll:>+5.1f}°\n"
                # Line 2 — Engines
                f"  RPM  L:{rpm_l:>4.0f}% {bar(rpm_l,0,100)}  "
                f"R:{rpm_r:>4.0f}% {bar(rpm_r,0,100)} | "
                f"Tmp L:{temp_l:>5.0f}°  R:{temp_r:>5.0f}° | "
                f"Flow:{flow_rate:>5.0f}kg/m | "
                f"Fuel:{fuel_int:>6.0f}kg\n"
                # Line 3 — Rates + Wind
                f"  Rates P:{pitch_rate:>+6.1f} R:{roll_rate:>+6.1f} Y:{yaw_rate:>+6.1f} °/s | "
                f"Wind X:{wind_x:>+5.1f} Y:{wind_y:>+5.1f} Z:{wind_z:>+5.1f} | "
                f"Pkts:{packet_count:>6d}\n"
                # Line 4 — Status
                f"  {status}"
            )
            print(dash + f"\033[{LINES}A", end="", flush=True)

        except socket.timeout:
            continue

        except KeyboardInterrupt:
            print(f"\033[{LINES}B")
            print(f"\n  Capture stopped.")
            print(f"  Total packets  : {packet_count}")
            print(f"  Fault packets  : {fault_packets}")
            print(f"  Bad packets    : {bad_packets}")
            print(f"  CSV saved to   : {csv_filename}")
            break