#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.lines as mlines
import glob, os, re, sys, csv
from collections import defaultdict
from ieee_style import apply_ieee_style, clean_ax

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG & IEEE THESIS STYLING
# ─────────────────────────────────────────────────────────────────────────────
LOGS_DIR   = "logs"
OUT_DIR    = "Results/FOM"
OUT_PLOTS  = os.path.join(OUT_DIR, "Power_Plots")
DEVICE_WIDTH_MM = 0.1  

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(OUT_PLOTS, exist_ok=True)

apply_ieee_style()
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman']
mpl.rcParams['mathtext.fontset'] = 'stix'
mpl.rcParams['font.size'] = 11
mpl.rcParams['axes.labelsize'] = 11
mpl.rcParams['axes.titlesize'] = 12
mpl.rcParams['legend.fontsize'] = 10
mpl.rcParams['xtick.labelsize'] = 10
mpl.rcParams['ytick.labelsize'] = 10

# ─────────────────────────────────────────────────────────────────────────────
# LOG PARSERS
# ─────────────────────────────────────────────────────────────────────────────
def get_contact_indices(filename):
    contacts = {}
    order = 0
    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith('w '):
                parts = line.split()
                if len(parts) >= 4:
                    contacts[parts[1].lower()] = {'electrode': parts[-1], 'order': order}
                    order += 1
    return contacts

def get_dynamic_codes(filename):
    contacts = get_contact_indices(filename)
    drain = contacts.get('drain')
    if drain is None: return {'vdrain': ['603', '4'], 'coss': '133'} 
    drain_idx = drain['electrode']
    return {'vdrain': [f'6{int(drain_idx):02d}', str(4 + drain['order'])], 'coss': f'1{drain_idx}{drain_idx}'}

def parse_log(filepath, code_map):
    col_names, rows = [], []
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line.startswith('p '):
                    for code in line.split()[2:]:
                        col_names.append(code_map.get(code, 'skip'))
                elif line.startswith('d '):
                    rows.append([float(x) for x in line.split()[1:]])
    except Exception: return None
    if not rows: return None
    data = np.array(rows)
    return {n: data[:, i] for i, n in enumerate(col_names) if n != 'skip'}

def get_sub_thickness(sub_str):
    if sub_str == 'Unknown': return 0.0
    try: return float(sub_str.split('_')[1].replace('µm', ''))
    except Exception: return 0.0

# ─────────────────────────────────────────────────────────────────────────────
# DATA EXTRACTION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
ron_dict = {}
sapphire_ron_baseline = {}

for fpath in sorted(glob.glob(os.path.join(LOGS_DIR, "*VD_Vg_*V*.log"))):
    base  = os.path.basename(fpath).replace('.log', '')
    lgd_m = re.search(r'Lgd(\d+)', base)
    buf_m = re.search(r'Buffer_([\d._]+)um', base)
    sub_m = re.search(r'Substrate_([A-Za-z]+)_([\d._]+)um', base, re.IGNORECASE)
    fp_m  = re.search(r'gate_source_FP', base, re.IGNORECASE)
    
    if not (lgd_m and buf_m): continue

    lgd = float(lgd_m.group(1))
    buf = float(buf_m.group(1).replace('_', '.'))
    sub = f"{sub_m.group(1).capitalize()}_{sub_m.group(2)}µm" if sub_m else 'Unknown'
    fp  = 'GS_FP' if fp_m else 'Std'

    data = parse_log(fpath, {"4": "vdrain", "22": "idrain"})
    if data is None: continue

    vd, id_ = data['vdrain'], data['idrain']
    mask = (vd >= 0.1) & (vd <= 0.5)
    
    if not np.any(mask): continue
    slope = np.polyfit(vd[mask], id_[mask], 1)[0]
    if slope <= 0: continue
    ron = 1.0 / slope   

    key = (lgd, buf, sub, fp)
    ron_dict[key] = ron
    if 'Sapphire' in sub:
        sapphire_ron_baseline[(lgd, buf, fp)] = ron

vbr_dict = {}
for fpath in sorted(glob.glob(os.path.join(LOGS_DIR, "*Vbr*.log"))):
    base  = os.path.basename(fpath).replace('.log', '')
    lgd_m = re.search(r'Lgd(\d+)', base)
    buf_m = re.search(r'Buffer_([\d._]+)um', base)
    sub_m = re.search(r'Substrate_([A-Za-z]+)_([\d._]+)um', base, re.IGNORECASE)
    fp_m  = re.search(r'gate_source_FP', base, re.IGNORECASE)
    
    if not (lgd_m and buf_m): continue

    lgd = float(lgd_m.group(1))
    buf = float(buf_m.group(1).replace('_', '.'))
    sub = f"{sub_m.group(1).capitalize()}_{sub_m.group(2)}µm" if sub_m else 'Unknown'
    fp  = 'GS_FP' if fp_m else 'Std'

    data = parse_log(fpath, {"4": "vdrain", "22": "idrain"})
    if data is None: continue

    vd = data['vdrain']
    valid_indices = np.where(vd > 50)[0] 
    vbr_dict[(lgd, buf, sub, fp)] = float(np.max(vd[valid_indices])) if len(valid_indices) > 1 else np.nan

cap_dict = {}
for fpath in sorted(glob.glob(os.path.join(LOGS_DIR, "*Cap*.log"))):
    base  = os.path.basename(fpath).replace('.log', '')
    lgd_m = re.search(r'Lgd(\d+)', base)
    buf_m = re.search(r'Buffer_([\d._]+)um', base)
    sub_m = re.search(r'Substrate_([A-Za-z]+)_([\d._]+)um', base, re.IGNORECASE)
    fp_m  = re.search(r'gate_source_FP', base, re.IGNORECASE)
    
    if not (lgd_m and buf_m): continue

    lgd = float(lgd_m.group(1))
    buf = float(buf_m.group(1).replace('_', '.'))
    sub = f"{sub_m.group(1).capitalize()}_{sub_m.group(2)}µm" if sub_m else 'Unknown'
    fp  = 'GS_FP' if fp_m else 'Std'

    codes = get_dynamic_codes(fpath)
    code_map = {codes['coss']: 'coss'}
    for vc in codes['vdrain']: code_map[vc] = 'vdrain'

    data = parse_log(fpath, code_map)
    if data is None or 'vdrain' not in data or 'coss' not in data: continue

    vd = data['vdrain']
    coss_raw = np.abs(data['coss']) 
    
    dx = np.diff(vd)
    y1_E, y2_E = (coss_raw[:-1] * vd[:-1]), (coss_raw[1:] * vd[1:])
    dE = (y1_E + y2_E) / 2 * dx
    Eoss_J = np.concatenate(([0], np.cumsum(dE)))

    Coer_F = np.where(vd > 0.1, (2 * Eoss_J) / (vd**2), coss_raw[0])
    Coer_pF = (Coer_F / DEVICE_WIDTH_MM) * 1e12 

    cap_dict[(lgd, buf, sub, fp)] = {
        'c600':  float(Coer_pF[np.argmin(np.abs(vd - 600))])
    }

# ─────────────────────────────────────────────────────────────────────────────
# MERGING & CSV TABLE EXPORT
# ─────────────────────────────────────────────────────────────────────────────
fom_data = []
all_device_keys = set(vbr_dict.keys()).intersection(set(cap_dict.keys()))

for key in all_device_keys:
    lgd, buf, sub, fp = key
    ron = None
    
    if key in ron_dict: ron = ron_dict[key]
    elif (lgd, buf, sub, 'Std') in ron_dict: ron = ron_dict[(lgd, buf, sub, 'Std')]
    elif 'Si' in sub and (lgd, buf, fp) in sapphire_ron_baseline: ron = sapphire_ron_baseline[(lgd, buf, fp)] * 1.011
    elif 'Si' in sub and (lgd, buf, 'Std') in sapphire_ron_baseline: ron = sapphire_ron_baseline[(lgd, buf, 'Std')] * 1.011
        
    if ron is None: continue 

    vbr = vbr_dict[key]         
    cap = cap_dict[key]
    
    hf_fom_600 = ron * cap['c600']
    
    fom_data.append({
        'lgd': lgd, 'buf': buf, 'sub': sub, 'fp': fp,
        'sub_thk': get_sub_thickness(sub), 'sub_type': 'Sapphire' if 'Sapphire' in sub else 'Silicon',
        'ron': ron, 'vbr': vbr, 'c600': cap['c600'], 'hf_fom_600': hf_fom_600
    })

print(f"Data compiled successfully for {len(fom_data)} devices.")

# Export Excel/CSV Table ranked by FOM
fom_data.sort(key=lambda x: x['hf_fom_600'])
csv_path = os.path.join(OUT_DIR, "FOM_Ranked_Table.csv")
with open(csv_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Rank', 'Material', 'Lgd_um', 'Buf_um', 'Sub_Thk_um', 'FP_Type', 'Rds_on (Ohm.mm)', 'Coer_600V (pF/mm)', 'Vbr (V)', 'FOM (Ohm.pF)'])
    for idx, d in enumerate(fom_data, start=1):
        writer.writerow([idx, d['sub_type'], d['lgd'], d['buf'], d['sub_thk'], d['fp'], 
                         f"{d['ron']:.4f}", f"{d['c600']:.4f}", f"{d['vbr']:.1f}", f"{d['hf_fom_600']:.2f}"])
print(f"Excel table (CSV) saved to {csv_path}")

# ─────────────────────────────────────────────────────────────────────────────
# GENERATE HIGH-FREQUENCY FOM POWER PLOT (INTEGRATED CORNER LEGENDS)
# ─────────────────────────────────────────────────────────────────────────────
print("Generating High-Frequency Performance Power Plot...")

fig, ax = plt.subplots(figsize=(9, 6.5))

colors_sap = {5.0: '#48CAE4', 50.0: '#0096C7', 500.0: '#023E8A'}
colors_si  = {5.0: '#FF758F', 50.0: '#E63946', 500.0: '#780000'}

trajectory_groups_hf = defaultdict(list)
for d in fom_data:
    if not np.isnan(d['vbr']):
        key = (d['sub_thk'], d['buf'], d['fp'], d['sub_type'])
        trajectory_groups_hf[key].append((d['lgd'], d['vbr'], d['hf_fom_600']))

for key, pts in trajectory_groups_hf.items():
    pts.sort(key=lambda x: x[0])  
    lgds = [p[0] for p in pts]
    vbrs = [p[1] for p in pts]
    foms = [p[2] for p in pts]
    
    sub_thk = key[0]
    buf = key[1]
    sub_type = key[3]
    
    c = colors_sap.get(sub_thk, '#023E8A') if sub_type == 'Sapphire' else colors_si.get(sub_thk, '#780000')
    marker = 'o' if sub_type == 'Sapphire' else 's'
    ls = '-' if buf == 0.5 else '--'
    fc = c if buf == 0.5 else 'white'
    
    ax.plot(vbrs, foms, color=c, linewidth=1.5, linestyle=ls, alpha=0.5, zorder=2)
    
    for i in range(len(vbrs) - 1):
        ax.annotate('', 
                    xy=(vbrs[i+1], foms[i+1]), 
                    xytext=(vbrs[i], foms[i]),
                    arrowprops=dict(arrowstyle="->", color=c, lw=1.5, alpha=0.8, shrinkA=12, shrinkB=12),
                    zorder=2)
    
    for l, v, f in zip(lgds, vbrs, foms):
        s_size = 50 if l <= 10 else (120 if l <= 15 else 220)
        ax.scatter([v], [f], marker=marker, facecolors=fc, edgecolors=c, s=s_size, linewidths=1.5, alpha=0.9, zorder=3)

# Target line
ax.axvline(1200, color='black', linestyle=':', linewidth=2, zorder=1)

ax.set_xscale('log')
ax.set_yscale('log')
ax.margins(0.15)

clean_ax(ax, xlabel=r'Breakdown Voltage $V_{br}$ (V)', ylabel=r'Hard-Switching FOM: $R_{on} \times C_{o(er)}$ ($\Omega\cdot$pF)', legend=False)
ax.set_title(r'High-Frequency Performance Power Plot', fontweight='bold', fontsize=14)
ax.grid(True, which='both', linestyle=':', alpha=0.5)

# ─────────────────────────────────────────────────────────────────────────────
# IN-PLOT CORNER LEGENDS
# ─────────────────────────────────────────────────────────────────────────────

# 1. Top-Left: Substrate Material
handles_mat = [
    mlines.Line2D([], [], color='grey', marker='o', markersize=8, linestyle='none', label='Sapphire'),
    mlines.Line2D([], [], color='grey', marker='s', markersize=8, linestyle='none', label='Silicon')
]
leg1 = ax.legend(handles=handles_mat, loc='upper left', title='Substrate Material', 
                 title_fontproperties={'weight':'bold'}, edgecolor='black', framealpha=1)
ax.add_artist(leg1)

# 2. Top-Right: Lateral Geometry
handles_lgd = [
    mlines.Line2D([], [], color='grey', marker='o', markersize=5, linestyle='none', label=r'$L_{gd}=10$ µm'),
    mlines.Line2D([], [], color='grey', marker='o', markersize=8, linestyle='none', label=r'$L_{gd}=15$ µm'),
    mlines.Line2D([], [], color='grey', marker='o', markersize=12, linestyle='none', label=r'$L_{gd}=20$ µm')
]
leg2 = ax.legend(handles=handles_lgd, loc='upper right', title='Lateral Geometry', 
                 title_fontproperties={'weight':'bold'}, edgecolor='black', framealpha=1)
ax.add_artist(leg2)

# 3. Bottom-Left: Substrate Thickness
handles_thk = [
    mlines.Line2D([], [], color='#023E8A', marker='s', markersize=9, linestyle='none', label='500 µm (Darkest)'),
    mlines.Line2D([], [], color='#0096C7', marker='s', markersize=9, linestyle='none', label='50 µm (Medium)'),
    mlines.Line2D([], [], color='#48CAE4', marker='s', markersize=9, linestyle='none', label='5 µm (Lightest)')
]
leg3 = ax.legend(handles=handles_thk, loc='lower left', title='Substrate Thickness', 
                 title_fontproperties={'weight':'bold'}, edgecolor='black', framealpha=1)
ax.add_artist(leg3)

# 4. Bottom-Right: Vertical Stack (Buffer)
handles_buf = [
    mlines.Line2D([], [], color='grey', marker='o', markerfacecolor='grey', markersize=8, linestyle='-', label='0.5 µm Buffer'),
    mlines.Line2D([], [], color='grey', marker='o', markerfacecolor='white', markeredgewidth=1.5, markersize=8, linestyle='--', label='5.0 µm Buffer')
]
leg4 = ax.legend(handles=handles_buf, loc='lower right', title='Vertical Stack', 
                 title_fontproperties={'weight':'bold'}, edgecolor='black', framealpha=1)
ax.add_artist(leg4)

plt.tight_layout()
fig.savefig(os.path.join(OUT_PLOTS, "PowerPlot_HighFrequency_FOM.png"), dpi=300, bbox_inches='tight')
plt.close(fig)

print("Main Plot successfully generated with all 4 inline boxed legends in Results/FOM/Power_Plots/")