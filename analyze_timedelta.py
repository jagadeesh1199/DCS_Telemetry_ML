import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =====================
# FILES
# =====================
files = {
    '15m Altitude': 'flight_data_20260323_221137.csv',
    '5km Altitude': 'flight_data_20260323_221325.csv',
    '8km Altitude': 'flight_data_20260323_221518.csv'
}

results = []

fig, axes = plt.subplots(3, 1, figsize=(16, 16))
plt.subplots_adjust(hspace=0.5)

# =====================
# ACTIVATION DETECTION FUNCTION
# =====================
def detect_activation(signal, baseline, percent_rise=0.05):
    """
    Detect activation for gradual, physics-driven signals.
    Uses smoothed cumulative deviation + derivative refinement.
    """
    smooth = signal.rolling(5, min_periods=1).mean()
    cumsum = smooth - smooth.iloc[0]
    total_rise = smooth.max() - smooth.min()
    threshold = percent_rise * total_rise

    candidates = cumsum[cumsum >= threshold]
    if len(candidates) > 0:
        derivative = smooth.diff().abs()
        base_smooth = baseline.rolling(5, min_periods=1).mean()
        base_derivative = base_smooth.diff().abs()
        derivative_threshold = base_derivative.mean() + 1.5 * base_derivative.std()
        candidates_refined = derivative[candidates.index] > derivative_threshold
        if candidates_refined.any():
            return derivative[candidates.index][candidates_refined].index[0]
        return candidates.index[0]

    return smooth.idxmax()

# =====================
# LOOP THROUGH FILES
# =====================
for i, (label, filepath) in enumerate(files.items()):
    print(f"\nProcessing: {label}")

    # 1. LOAD DATA
    df = pd.read_csv(filepath)
    df['Time'] = pd.to_timedelta(df['Time'], unit='s')
    df.set_index('Time', inplace=True)

    # 2. RESAMPLE (preserve gradients)
    df_clean = df.resample('25ms').interpolate(limit=2)

    # 3. FAULT TIME
    if df_clean['Fire_L'].sum() > 0:
        t_fault = df_clean[df_clean['Fire_L'] >= 0.5].index[0]
    else:
        rpm_diff_full = abs(df_clean['RPM_L'] - df_clean['RPM_R'])
        t_fault = rpm_diff_full[rpm_diff_full > rpm_diff_full.mean() + 3*rpm_diff_full.std()].index[0]

    # 4. WINDOW
    window = df_clean[(df_clean.index >= t_fault - pd.Timedelta(seconds=1)) &
                      (df_clean.index <= t_fault + pd.Timedelta(seconds=3))]
    time_axis = (window.index - t_fault).total_seconds()

    # 5. BASELINE NORMALIZATION
    baseline = df_clean.loc[t_fault - pd.Timedelta(seconds=3):t_fault]

    # Aero domain normalization
    aero_signals = ['RollRate', 'PitchRate', 'YawRate', 'Roll', 'Pitch', 'Yaw', 'AoA', 'TAS', 'Mach', 'VSI']
    aero_norm = window[aero_signals].copy()
    for col in aero_signals:
        aero_norm[col] -= baseline[col].mean()

    # Mechanical domain
    mech_signals = ['RPM_L', 'RPM_R', 'FuelFlow_L', 'FuelFlow_R', 'Fuel_Internal']
    mech_diff = abs(window['RPM_L'] - window['RPM_R'])
    mech_base_diff = abs(baseline['RPM_L'] - baseline['RPM_R'])

    # Thermal domain
    temp_diff = abs(window['Temp_L'] - window['Temp_R'])
    temp_base_diff = abs(baseline['Temp_L'] - baseline['Temp_R'])

    # Systems domain (Hydraulic + Warnings)
    sys_signals = ['Hyd_Fail', 'Master_Warn', 'ACS_Active', 'EOS_Active', 'Fire_L', 'Fire_R']
    sys_norm = window[sys_signals].copy()
    for col in sys_signals:
        sys_norm[col] -= baseline[col].mean()

    # 6. ACTIVATION DETECTION
    t_aero = detect_activation(abs(aero_norm['YawRate']), baseline['YawRate'])
    t_thermal = detect_activation(temp_diff, temp_base_diff)
    t_mech = detect_activation(mech_diff, mech_base_diff)
    # For systems, take max deviation across all system signals
    sys_max = sys_norm.abs().max(axis=1)
    sys_base_max = baseline[sys_signals].abs().max(axis=1)
    t_system = detect_activation(sys_max, sys_base_max)

    # 7. COMPUTE DELAYS
    def compute_dt(t_domain):
        return (t_domain - t_aero).total_seconds() if t_domain and t_aero else np.nan

    dt_thermal = compute_dt(t_thermal)
    dt_mech = compute_dt(t_mech)
    dt_system = compute_dt(t_system)

    print(f"Aero: {t_aero}, Thermal: {t_thermal}, Mechanical: {t_mech}, Systems: {t_system}")
    print(f"ΔT Thermal: {dt_thermal:.4f}, ΔT Mechanical: {dt_mech:.4f}, ΔT Systems: {dt_system:.4f}")

    results.append({
        'Altitude': label,
        'ΔT Thermal (s)': dt_thermal,
        'ΔT Mechanical (s)': dt_mech,
        'ΔT Systems (s)': dt_system
    })

    # 8. PLOTTING
    ax = axes[i]

    # Normalize for plotting
    rpm_norm = (mech_diff - mech_diff.min()) / (mech_diff.max() - mech_diff.min() + 1e-6)
    temp_norm = (temp_diff - temp_diff.min()) / (temp_diff.max() - temp_diff.min() + 1e-6)
    yaw_plot = aero_norm['YawRate']

    ax.plot(time_axis, yaw_plot, label='Yaw Rate (Aero)', linewidth=2)
    ax.plot(time_axis, temp_norm, label='Temp Diff (Thermal)', linestyle='--')
    ax.plot(time_axis, rpm_norm, label='RPM Diff (Mechanical)', linestyle='-.')
    ax.plot(time_axis, sys_max, label='System Max', linestyle=':')

    ax.axvline(0, linestyle='--', alpha=0.5, label='Fault Trigger')

    def mark(ax, t, label, color):
        if t is not None:
            ax.axvline((t - t_fault).total_seconds(), linestyle=':', label=label)

    mark(ax, t_aero, 'Aero Activation', 'orange')
    mark(ax, t_thermal, 'Thermal Activation', 'green')
    mark(ax, t_mech, 'Mechanical Activation', 'purple')
    mark(ax, t_system, 'System Activation', 'red')

    ax.set_title(f"Cross-Domain Fault Propagation — {label}")
    ax.set_xlabel("Time since fault (s)")
    ax.set_ylabel("Normalized / Rate")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_xlim(-0.5, 2.5)

# 9. RESULTS TABLE
results_df = pd.DataFrame(results)
print("\n=== TEMPORAL DELAYS SUMMARY ===")
print(results_df)
results_df.to_csv("temporal_delay_summary.csv", index=False)

# 10. SAVE FIGURE
plt.tight_layout()
plt.savefig("cross_domain_propagation_full.png", dpi=300)
plt.show()

# 11. TRANSFORMER SEQUENCES PREPARATION
sequence_length = 50  # timesteps
all_sequences = []
all_labels = []

all_signals = aero_signals + mech_signals + ['Temp_L', 'Temp_R'] + sys_signals + ['Alt_Radar', 'Alt_Baro', 'Wind_X', 'Wind_Y', 'Wind_Z', 'Vel_X', 'Vel_Y', 'Vel_Z']

for label, filepath in files.items():
    df = pd.read_csv(filepath)
    df['Time'] = pd.to_timedelta(df['Time'], unit='s')
    df.set_index('Time', inplace=True)
    df_clean = df.resample('25ms').interpolate(limit=2)
    
    # normalize signals
    signals = df_clean[all_signals].copy()
    signals = (signals - signals.mean()) / (signals.std() + 1e-6)
    
    # sliding window sequences
    for start in range(len(signals) - sequence_length):
        seq = signals.iloc[start:start + sequence_length].values
        all_sequences.append(seq)
        all_labels.append(label)  # or fault type

all_sequences = np.array(all_sequences)
all_labels = np.array(all_labels)

print(f"Prepared {all_sequences.shape[0]} multi-domain sequences for Transformer input.")