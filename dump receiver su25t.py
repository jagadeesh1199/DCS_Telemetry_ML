import socket
import csv
import datetime
import os

# ── CONFIGURATION ────────────────────────────────────────────────────────────
UDP_IP      = "127.0.0.1"
UDP_PORT    = 55000
BUFFER_SIZE = 8192

# ── HEADERS — must match Export_Su25T_Enhanced.lua exactly (46 columns) ─────
HEADERS = [
    "Time", "Alt_Radar", "VSI", "TAS", "Mach", "AoA", "SideSlip", "G_Load",
    "Pitch", "Roll", "Yaw",
    "RPM_L", "RPM_R", "Temp_L", "Temp_R",
    "Gear", "Flaps", "Airbrake",
    "Hyd_Fail", "FuelFlow_L", "FuelFlow_R",
    "Cannon_Shells", "Flares", "Chaff",
    "Master_Warn", "ACS_Active", "EOS_Active", "Fire_L", "Fire_R",
    "Wind_X", "Wind_Y", "Wind_Z",
    "RollRate", "PitchRate", "YawRate",
    "Vel_X", "Vel_Y", "Vel_Z",
    "Throttle_L", "Throttle_R",
    "Stick_Pitch", "Stick_Roll", "Rudder",
    "Fuel_Internal", "Fuel_External", "Alt_Baro",
]

EXPECTED_COLS = len(HEADERS)  # 46
IDX = {h: i for i, h in enumerate(HEADERS)}

# ── NETWORK ──────────────────────────────────────────────────────────────────
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.settimeout(1.0)

# ── FILE ─────────────────────────────────────────────────────────────────────
timestamp    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"flight_data_{timestamp}.csv"

# ── STARTUP BANNER ───────────────────────────────────────────────────────────
os.system("cls" if os.name == "nt" else "clear")
print("-" * 65)
print("  DIGITAL TWIN RECEIVER — Su-25T Enhanced")
print(f"  Listening on port : {UDP_PORT}")
print(f"  Recording to      : {csv_filename}")
print(f"  Expecting columns : {EXPECTED_COLS}")
print("-" * 65)
print("  Waiting for aircraft data stream...")
print()

# ── HELPERS ──────────────────────────────────────────────────────────────────
def bar(value, lo, hi, width=10, fill="█", empty="░"):
    frac   = max(0.0, min(1.0, (value - lo) / (hi - lo) if hi != lo else 0))
    filled = round(frac * width)
    return fill * filled + empty * (width - filled)

def sign_bar(value, width=7):
    half = width // 2
    pos  = round(abs(value) * half)
    if value >= 0:
        left  = "░" * half
        right = "█" * pos + "░" * (half - pos)
    else:
        left  = "░" * (half - pos) + "█" * pos
        right = "░" * half
    return left + "|" + right

# ── MAIN LOOP ────────────────────────────────────────────────────────────────
with open(csv_filename, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(HEADERS)

    packet_count  = 0
    fault_packets = 0
    bad_packets   = 0
    dump_packets  = 0
    in_dump_mode  = False

    while True:
        try:
            data, _ = sock.recvfrom(BUFFER_SIZE)
            decoded = data.decode("utf-8").strip()

            # ── ARG DUMP HEARTBEAT ────────────────────────────────────────────
            # Lua sends "DUMP,<time>,<col_count>" while ARG_DUMP_MODE = true.
            # Actual dump CSV is written by Lua directly to disk — not here.
            if decoded.startswith("DUMP,"):
                parts     = decoded.split(",")
                dump_t    = parts[1] if len(parts) > 1 else "?"
                dump_cols = parts[2] if len(parts) > 2 else "?"
                dump_packets += 1
                if not in_dump_mode:
                    in_dump_mode = True
                    print(
                        f"\n  [ARG DUMP MODE] Scanning {dump_cols} device+arg combos.\n"
                        f"  Move ONE control at a time — slow full deflection each way.\n"
                        f"  Dump CSV: Saved Games/DCS/Telemetry_ArgDump.csv\n"
                        f"  When done: set ARG_DUMP_MODE = false in the Lua script.\n"
                    )
                print(
                    f"\r  Dump running  T:{dump_t:>8s}s  rows: {dump_packets:>6d}",
                    end="", flush=True
                )
                continue

            # Dump mode just ended — normal telemetry starting
            if in_dump_mode:
                in_dump_mode = False
                print(f"\n\n  [INFO] Dump ended — normal telemetry stream active.\n")

            # ── PARSE ─────────────────────────────────────────────────────────
            values = decoded.split(",")

            # ── INTEGRITY CHECK ───────────────────────────────────────────────
            if len(values) != EXPECTED_COLS:
                bad_packets += 1
                if bad_packets <= 5:
                    print(
                        f"\n  [WARN] Expected {EXPECTED_COLS} cols, got {len(values)}"
                        f" — packet #{packet_count + 1}\n"
                        f"  Check ARG_DUMP_MODE=false and KNOWN_ARGS are filled in.\n"
                    )
                continue

            # ── WRITE TO CSV ──────────────────────────────────────────────────
            writer.writerow(values)
            packet_count += 1
            if packet_count % 250 == 0:
                f.flush()

            # ── PARSE VALUES ──────────────────────────────────────────────────
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
            slip       = fv("SideSlip")
            g_load     = fv("G_Load")
            pitch      = fv("Pitch")
            roll       = fv("Roll")
            rpm_l      = fv("RPM_L")
            rpm_r      = fv("RPM_R")
            temp_l     = fv("Temp_L")
            temp_r     = fv("Temp_R")
            ff_l       = fv("FuelFlow_L")
            ff_r       = fv("FuelFlow_R")
            thr_l      = fv("Throttle_L")
            thr_r      = fv("Throttle_R")
            stk_p      = fv("Stick_Pitch")
            stk_r      = fv("Stick_Roll")
            rudder     = fv("Rudder")
            roll_rate  = fv("RollRate")
            pitch_rate = fv("PitchRate")
            yaw_rate   = fv("YawRate")
            wind_x     = fv("Wind_X")
            wind_y     = fv("Wind_Y")
            fuel_int   = fv("Fuel_Internal")
            shells     = iv("Cannon_Shells")
            flares     = iv("Flares")
            chaff      = iv("Chaff")
            fire_l     = iv("Fire_L")
            fire_r     = iv("Fire_R")
            mwarn      = iv("Master_Warn")
            hyd        = iv("Hyd_Fail")
            gear       = fv("Gear")
            flaps      = fv("Flaps")
            airbrake   = fv("Airbrake")

            flow_rate = (ff_l + ff_r) * 60  # kg/min

            if fire_l or fire_r:
                fault_packets += 1

            # ── STATUS ────────────────────────────────────────────────────────
            if   fire_l and fire_r: status = "*** DUAL ENGINE FIRE ***"
            elif fire_l:            status = "*** FIRE LEFT ENGINE  ***"
            elif fire_r:            status = "*** FIRE RIGHT ENGINE ***"
            elif hyd:               status = "*** HYD FAILURE       ***"
            elif mwarn:             status = "*** MASTER CAUTION    ***"
            elif thr_l < 0.05:      status = "<<< THR-L CUTOFF"
            elif thr_r < 0.05:      status = "<<< THR-R CUTOFF"
            elif rpm_l < 50:        status = "<<< RPM-L LOW"
            elif rpm_r < 50:        status = "<<< RPM-R LOW"
            else:                   status = "SYSTEMS OK"

            # ── LIVE DASHBOARD (5-line overwriting block) ─────────────────────
            LINES = 5
            dash = (
                f"  T:{t_val:>7.1f}s | "
                f"Alt:{alt:>6.0f}m | "
                f"VSI:{vsi:>+6.1f} | "
                f"M:{mach:.3f} | "
                f"AoA:{aoa:>+5.1f}° | "
                f"Slip:{slip:>+6.2f}° | "
                f"G:{g_load:>+4.1f} | "
                f"Pitch:{pitch:>+5.1f}° Roll:{roll:>+5.1f}°\n"
                f"  RPM  L:{rpm_l:>4.0f}% {bar(rpm_l,0,100)}  "
                f"R:{rpm_r:>4.0f}% {bar(rpm_r,0,100)} | "
                f"Tmp L:{temp_l:>4.0f}°  R:{temp_r:>4.0f}° | "
                f"Flow:{flow_rate:>5.0f}kg/m | "
                f"Fuel:{fuel_int:>6.0f}kg\n"
                f"  THR  L:{thr_l:>5.3f} {bar(thr_l,0,1)}  "
                f"R:{thr_r:>5.3f} {bar(thr_r,0,1)} | "
                f"Gear:{gear:.0f} Flaps:{flaps:.2f} Brk:{airbrake:.2f}\n"
                f"  STICK Ptch:{stk_p:>+5.3f} {sign_bar(stk_p)}  "
                f"Roll:{stk_r:>+5.3f} {sign_bar(stk_r)} | "
                f"RUDDER:{rudder:>+5.3f} {sign_bar(rudder)} | "
                f"Rates P:{pitch_rate:>+6.1f} R:{roll_rate:>+6.1f} Y:{yaw_rate:>+6.1f} °/s\n"
                f"  Ammo:{shells:>3d} Flares:{flares:>3d} Chaff:{chaff:>3d} | "
                f"Wind X:{wind_x:>+5.1f} Y:{wind_y:>+5.1f} | "
                f"Pkts:{packet_count:>6d} | {status}"
            )
            print(dash + f"\033[{LINES}A", end="", flush=True)

        except socket.timeout:
            continue

        except KeyboardInterrupt:
            print(f"\033[{LINES}B")
            print(f"\n  Capture stopped.")
            print(f"  Total packets  : {packet_count}")
            print(f"  Dump packets   : {dump_packets}")
            print(f"  Fault packets  : {fault_packets}")
            print(f"  Bad packets    : {bad_packets}")
            print(f"  CSV saved to   : {csv_filename}")
            break