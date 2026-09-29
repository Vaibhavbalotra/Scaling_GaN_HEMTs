#!/usr/bin/env python3
"""
Master Capacitance & Energy Analysis Pipeline (Final Thesis Version)
- Computes exact mathematical integrals for Qoss and Eoss.
- Generates a single unified comparative folder (Si_Sap_FP) and master CSV table.
- Generates the three primary presentation figures: Dielectric Scaling, Coer Reduction, and the Dual-Axis Sweep.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import os
import glob
import re
import sys
import math
import csv
from collections import defaultdict
from scipy.interpolate import make_interp_spline
from ieee_style import (apply_ieee_style, clean_ax)

# ==========================================================
# SETUP & STRICT IEEE THESIS STYLING
# ==========================================================
apply_ieee_style()
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman']
mpl.rcParams['mathtext.fontset'] = 'stix'
mpl.rcParams['font.size'] = 11
mpl.rcParams['axes.labelsize'] = 11
mpl.rcParams['legend.fontsize'] = 10
mpl.rcParams['xtick.labelsize'] = 10
mpl.rcParams['ytick.labelsize'] = 10

DEVICE_WIDTH_MM = 0.1
LOGS_DIR = 'logs/*.log'  

# Final Directories
DIR_SI_SAP_FP = 'Results/Capacitance/Si_Sap_FP'
OUT_THESIS = 'Results/Capacitance/Thesis_Comparisons'

for d in [DIR_SI_SAP_FP, OUT_THESIS]:
    os.makedirs(d, exist_ok=True)

# ── High Contrast Color Palettes ──────────────────────────────────────────────
C_SI_GRADIENT  = ['#FF758F', '#E63946', '#C1121F', '#780000', '#370617']
C_SAP_GRADIENT = ['#48CAE4', '#0096C7', '#023E8A', '#03045E', '#000000']

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
    gate = contacts.get('gate')
    drain = contacts.get('drain')

    if gate is None or drain is None:
        return {'vdrain': ['603', '4'], 'ciss': '122', 'crss': '123', 'coss': '133'}

    gate_idx, drain_idx = gate['electrode'], drain['electrode']
    vdrain_electrode_code = f'6{int(drain_idx):02d}'
    vdrain_sequential_code = str(4 + drain['order'])
    vdrain_codes = [vdrain_electrode_code, vdrain_sequential_code]

    ciss_code = f'1{gate_idx}{gate_idx}'
    crss_code = f'1{gate_idx}{drain_idx}'
    coss_code = f'1{drain_idx}{drain_idx}'
    return {'vdrain': vdrain_codes, 'ciss': ciss_code, 'crss': crss_code, 'coss': coss_code}

def read_cap(filename, code_name, vdrain_codes):
    col_names, all_rows = [], []
    try:
        with open(filename, 'r') as file:
            for line in file:
                line = line.strip()
                if line.startswith('p '):
                    codes = line.split()[2:]
                    for code in codes:
                        if code in vdrain_codes: col_names.append('vdrain')
                        elif code == code_name: col_names.append('cap')
                        else: col_names.append('skip')
                elif line.startswith('d '):
                    all_rows.append([float(x) for x in line.split()[1:]])
        data = np.array(all_rows)
        return {name: data[:, i] for i, name in enumerate(col_names) if name != 'skip'}
    except Exception: return None

def despike(data, window=7):
    pad = window // 2
    padded = np.pad(data, (pad, pad), mode='edge')
    return np.array([np.median(padded[i:i+window]) for i in range(len(data))])

# ==========================================================
# DATA EXTRACTION & RIGOROUS MATH CALCULATION
# ==========================================================
master_data = []
print("Scanning log files, filtering TCAD noise, and computing integrals...")

for file_path in glob.glob(LOGS_DIR):
    base_name = os.path.basename(file_path).replace('.log', '')
    
    lgd_match = re.search(r'Lgd([\d.]+)', base_name, re.IGNORECASE)
    buf_match = re.search(r'Buffer_([\d.]+)um', base_name, re.IGNORECASE)
    sub_match = re.search(r'substrate_([A-Za-z]+)_([\d.]+)um', base_name, re.IGNORECASE)

    if not (lgd_match and buf_match and sub_match): continue

    lgd = float(lgd_match.group(1))
    buf = float(buf_match.group(1).replace('_', '.'))
    sub_type_raw = sub_match.group(1).capitalize()
    SUBSTRATE_ALIASES = {
        'Saphhire': 'Sapphire', 'Saphire': 'Sapphire', 'Sapphhire': 'Sapphire',
        'Sic': 'SiC', 'Silicone': 'Silicon', 'Si': 'Silicon'
    }
    sub_type = SUBSTRATE_ALIASES.get(sub_type_raw, sub_type_raw)
    sub_thk = float(sub_match.group(2).replace('_', '.'))
    sub_str = f"{sub_type} {sub_thk}µm"

    remainder = base_name[sub_match.end():]
    fp_match = re.match(r'_([A-Za-z_]+?)_Capacitance$', remainder, re.IGNORECASE)
    fp_raw = fp_match.group(1) if fp_match else 'Unknown'
    fp_key = fp_raw.lower()
    if 'gate' in fp_key and 'source' in fp_key:
        fp_type = 'GS-FP'
    elif 'gate' in fp_key:
        fp_type = 'G-FP'
    elif 'no' in fp_key:
        fp_type = 'No FP'
    else:
        fp_type = fp_raw

    clean_label = f"Lgd{lgd}_Buf{buf}_{sub_str}_{fp_type}"

    codes = get_dynamic_codes(file_path)
    ciss_raw = read_cap(file_path, codes['ciss'], codes['vdrain'])
    crss_raw = read_cap(file_path, codes['crss'], codes['vdrain'])
    coss_raw = read_cap(file_path, codes['coss'], codes['vdrain'])

    if not (ciss_raw and crss_raw and coss_raw and 'vdrain' in coss_raw):
        continue

    vd = coss_raw['vdrain']
    Coss_F = despike(abs(coss_raw['cap']), window=7)
    Crss_F = despike(abs(crss_raw['cap']), window=7)
    Ciss_F = despike(abs(ciss_raw['cap']), window=7)
    
    Ciss_pF = Ciss_F / DEVICE_WIDTH_MM * 1e12
    Crss_pF = Crss_F / DEVICE_WIDTH_MM * 1e12
    Coss_pF = Coss_F / DEVICE_WIDTH_MM * 1e12

    dx = np.diff(vd)
    
    y1_Q, y2_Q = Coss_F[:-1], Coss_F[1:]
    dQ = (y1_Q + y2_Q) / 2 * dx
    Qoss_F = np.concatenate(([0], np.cumsum(dQ)))
    
    y1_E, y2_E = (Coss_F[:-1] * vd[:-1]), (Coss_F[1:] * vd[1:])
    dE = (y1_E + y2_E) / 2 * dx
    Eoss_J = np.concatenate(([0], np.cumsum(dE)))

    Cotr_F = np.where(vd > 0.1, Qoss_F / vd, Coss_F[0])
    Coer_F = np.where(vd > 0.1, (2 * Eoss_J) / (vd**2), Coss_F[0])

    y1_Qgd, y2_Qgd = Crss_F[:-1], Crss_F[1:]
    dQgd = (y1_Qgd + y2_Qgd) / 2 * dx
    Qgd_F = np.concatenate(([0], np.cumsum(dQgd)))

    Eotr_J = 0.5 * Qoss_F * vd
    Eoer_J = Eoss_J

    Cotr_pF = Cotr_F / DEVICE_WIDTH_MM * 1e12
    Coer_pF = Coer_F / DEVICE_WIDTH_MM * 1e12
    Eotr_nJ = Eotr_J / DEVICE_WIDTH_MM * 1e9
    Eoer_nJ = Eoer_J / DEVICE_WIDTH_MM * 1e9
    Qgd_nC  = Qgd_F / DEVICE_WIDTH_MM * 1e9
    
    master_data.append({
        'label': clean_label, 'lgd': lgd, 'buf': buf, 'sub_type': sub_type, 'sub_thk': sub_thk,
        'fp_type': fp_type, 'vd': vd, 'Ciss': Ciss_pF, 'Crss': Crss_pF, 'Coss': Coss_pF, 
        'Cotr': Cotr_pF, 'Coer': Coer_pF, 'Eotr': Eotr_nJ, 'Eoer': Eoer_nJ, 'Qgd': Qgd_nC
    })

if not master_data:
    print("Error: No valid capacitance data found. Check your log files.")
    sys.exit()

print(f"Processed {len(master_data)} devices.")

# ==========================================================
# UNIFIED FOLDER GENERATION (Si_Sap_FP ONLY)
# ==========================================================
def slice_plot_metric(subset, save_path, omit_key, y_key, ylabel, log_y):
    if not subset: return
    
    fig, ax = plt.subplots(figsize=(6.5, 5.0))
    si_idx, sap_idx = 0, 0
    sorted_subset = sorted(subset, key=lambda x: (x['sub_type'], x['fp_type'], x['buf'], x['sub_thk']))
    
    for d in sorted_subset:
        if d['sub_type'] == 'Silicon':
            c = C_SI_GRADIENT[si_idx % len(C_SI_GRADIENT)]
            si_idx += 1
            mat_short = 'Si'
        else:
            c = C_SAP_GRADIENT[sap_idx % len(C_SAP_GRADIENT)]
            sap_idx += 1
            mat_short = 'Sap'
            
        ls = '--' if d['fp_type'] == 'GS-FP' else '-'
        
        attributes = []
        if omit_key != 'sub_thk':
            thk_val = int(d['sub_thk']) if d['sub_thk'].is_integer() else d['sub_thk']
            attributes.append(f"{thk_val} µm")
            
        if omit_key != 'lgd':
            attributes.append(f"$L$ {int(d['lgd'])}")
        if omit_key != 'buf':
            attributes.append(f"$buf$ {d['buf']}")
            
        fp_short = 'FP' if d['fp_type'] == 'GS-FP' else 'Std'
        attributes.append(fp_short)
        
        lbl = f"{mat_short} " + ", ".join(attributes)
        
        ax.plot(d['vd'], d[y_key], linewidth=2.0, color=c, linestyle=ls, label=lbl)
    
    clean_ax(ax, xlabel=r'Drain Voltage $V_{ds}$ (V)', ylabel=ylabel, legend=False)
    if log_y:
        ax.set_yscale('log')
    ax.set_xlim(0, 1500)
    
    num_items = len(ax.get_lines())
    calc_ncol = math.ceil(num_items / 3.0) if num_items > 0 else 1
    
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), 
              ncol=calc_ncol, frameon=True, edgecolor='black', columnspacing=1.0)
    
    fig.subplots_adjust(bottom=0.35)
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches='tight')
    plt.close(fig)

print("Generating unified Si_Sap_FP raw curve slices...")

metrics_to_slice = [
    ('Coss', r'Output Cap $C_{oss}$ (pF/mm)', True),
    ('Coer', r'Eq. Output Cap $C_{o(er)}$ (pF/mm)', True),
    ('Cotr', r'Time-Related Cap $C_{o(tr)}$ (pF/mm)', True),
    ('Eoer', r'Energy-Related Output Energy $E_{o(er)}$ (nJ/mm)', False),
    ('Eotr', r'Time-Related Output Energy $E_{o(tr)}$ (nJ/mm)', False),
    ('Crss', r'Reverse Transfer Cap $C_{rss}$ (pF/mm)', True),
    ('Qgd',  r'Miller Charge $Q_{gd}$ (nC/mm)', False)
]

for thk in sorted(set(d['sub_thk'] for d in master_data)):
    for y_key, ylabel, is_log in metrics_to_slice:
        subset_all = [d for d in master_data if d['sub_thk'] == thk]
        slice_plot_metric(subset_all, f"{DIR_SI_SAP_FP}/{y_key}_Fixed_Substrate_{thk}um", 
                          omit_key='sub_thk', y_key=y_key, ylabel=ylabel, log_y=is_log)

# ==========================================================
# MASTER CSV DATA TABLE EXPORT
# ==========================================================
print("Exporting master data table to CSV...")

def export_csv_table(subset, folder_path, filename="Capacitance_Energy_Values_Master.csv"):
    if not subset: return
    
    target_voltages = [300, 600, 900, 1200, 1500]
    params = ['Coss', 'Coer', 'Eoer', 'Cotr', 'Eotr', 'Crss', 'Qgd']
    
    sorted_subset = sorted(subset, key=lambda x: (x['sub_type'], x['fp_type'], x['sub_thk'], x['buf'], x['lgd']))
    csv_path = os.path.join(folder_path, filename)
    
    try:
        with open(csv_path, mode='w', newline='') as f:
            writer = csv.writer(f)
            
            header = ['Label', 'Material', 'Sub_Thk_um', 'Lgd_um', 'Buf_um', 'FP_Type']
            for param in params:
                for v in target_voltages:
                    header.append(f"{param}_{v}V")
            writer.writerow(header)
            
            for d in sorted_subset:
                row = [d['label'], d['sub_type'], d['sub_thk'], d['lgd'], d['buf'], d['fp_type']]
                vd = d['vd']
                for param in params:
                    y_data = d[param]
                    for v in target_voltages:
                        if max(vd) >= v:
                            val = np.interp(v, vd, y_data)
                            row.append(f"{val:.4f}")
                        else:
                            row.append("N/A") 
                writer.writerow(row)
    except PermissionError:
        print(f"\n[WARNING] Could not write to {csv_path}. Please close the file if it is open in Excel.")

export_csv_table(master_data, DIR_SI_SAP_FP)

# ==========================================================
# THESIS PRESENTATION PLOTS (Scaling, Reduction, & Dual-Axis Sweep)
# ==========================================================
print("Generating targeted thesis presentation plots...")

def get_y_val(mat, fp, v_target, y_key, lgd=None, buf=None, sub_thk=None):
    vals = []
    for d in master_data:
        if d['sub_type'] != mat or d['fp_type'] != fp: continue
        if lgd is not None and d['lgd'] != lgd: continue
        if buf is not None and d['buf'] != buf: continue
        if sub_thk is not None and d['sub_thk'] != sub_thk: continue
        if max(d['vd']) >= v_target:
            val = np.interp(v_target, d['vd'], d[y_key])
            if val > 0: vals.append(val)
    return min(vals) if vals else 0.0

sub_thks = [5.0, 50.0, 500.0]
available_lgds = sorted(list(set(d['lgd'] for d in master_data)))
available_bufs = sorted(list(set(d['buf'] for d in master_data)))
base_lgd = available_lgds[0] if available_lgds else 10.0
base_buf = available_bufs[1] if len(available_bufs) > 1 else available_bufs[0]

def plot_dielectric_scaling(filename):
    """
    Recreates Coer_App1_DielectricScaling.png showing multi-voltage Co(er) extraction
    across logarithmic substrate thickness axes.
    """
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    eval_voltages = [600, 900, 1200]
    
    colors_sap = {600: '#48CAE4', 900: '#0096C7', 1200: '#023E8A'}
    colors_si = {600: '#FF8FA3', 900: '#E63946', 1200: '#C1121F'}
    
    for v in eval_voltages:
        # Sapphire (Solid Lines with Circles)
        sap_y, sap_x = [], []
        for thk in sub_thks:
            val = get_y_val('Sapphire', 'No FP', v, 'Coer', lgd=base_lgd, buf=base_buf, sub_thk=thk)
            if val > 0:
                sap_y.append(val)
                sap_x.append(thk)
        if sap_y:
            ax.plot(sap_x, sap_y, marker='o', markersize=8, linewidth=2.5, color=colors_sap[v], label=f'Sapphire ({v} V)')
            
        # Silicon (Dashed Lines with Squares)
        si_y, si_x = [], []
        for thk in sub_thks:
            val = get_y_val('Silicon', 'No FP', v, 'Coer', lgd=base_lgd, buf=base_buf, sub_thk=thk)
            if val > 0:
                si_y.append(val)
                si_x.append(thk)
        if si_y:
            ax.plot(si_x, si_y, marker='s', markersize=8, linestyle='--', linewidth=2.5, color=colors_si[v], label=f'Silicon ({v} V)')
            
    ax.set_xscale('log')
    ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter())
    ax.set_xticks(sub_thks)
    clean_ax(ax, xlabel=r'Substrate Thickness $t_{sub}$ (µm)', ylabel=r'Eq. Output Cap $C_{o(er)}$ (pF/mm)', legend=False)
    ax.set_title(r'$C_{o(er)}$ vs. Substrate Thickness', fontweight='bold', fontsize=14)
    
    ax.legend(loc='upper right', edgecolor='black', ncol=2, fontsize=11)
    
    fig.tight_layout()
    fig.savefig(f'{OUT_THESIS}/{filename}.png', dpi=300, bbox_inches='tight')
    plt.close(fig)

def plot_approach_5(y_key, ylabel_prefix, filename):
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    eval_voltages = [600, 900, 1200]
    colors_red = ['#E63946', '#457B9D', '#1D3557'] 
    markers_red = ['D', 's', 'o']
    annotations = [] 

    for v_idx, v_target in enumerate(eval_voltages):
        reduction_vals, valid_thks = [], []
        for s_thk in sub_thks:
            c_si = get_y_val('Silicon', 'No FP', v_target, y_key, lgd=base_lgd, buf=base_buf, sub_thk=s_thk)
            c_sap = get_y_val('Sapphire', 'No FP', v_target, y_key, lgd=base_lgd, buf=base_buf, sub_thk=s_thk)
            if c_si > 0 and c_sap > 0:
                reduction = ((c_si - c_sap) / c_si) * 100.0
                reduction_vals.append(reduction)
                valid_thks.append(s_thk)
                annotations.append({'x': s_thk, 'y': reduction, 'text': f"{reduction:.1f}%", 'color': colors_red[v_idx]})

        if reduction_vals:
            ax.plot(valid_thks, reduction_vals, marker=markers_red[v_idx], color=colors_red[v_idx], 
                    linewidth=2.5, markersize=7, label=f'{v_target} V')

    ann_by_x = defaultdict(list)
    for ann in annotations: ann_by_x[ann['x']].append(ann)
        
    for x_val, anns in ann_by_x.items():
        anns = sorted(anns, key=lambda a: a['y'])
        offsets_y = [0] * len(anns)
        for _ in range(3): 
            for i in range(len(anns) - 1):
                y1 = anns[i]['y'] + offsets_y[i]
                y2 = anns[i+1]['y'] + offsets_y[i+1]
                if (y2 - y1) < 5.0: 
                    push = (5.0 - (y2 - y1)) / 2.0
                    offsets_y[i] -= push
                    offsets_y[i+1] += push
                    
        for ann, oy in zip(anns, offsets_y):
            pixel_offset = oy * 4 
            ax.annotate(ann['text'], (x_val, ann['y']), 
                        textcoords="offset points", xytext=(12, pixel_offset), ha='left', va='center',
                        fontsize=10, fontweight='bold', color=ann['color'],
                        bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=1))
            
    ax.set_xscale('log')
    ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter())
    ax.set_xticks(sub_thks)
    clean_ax(ax, xlabel=r'Substrate Thickness $t_{sub}$ (µm)', ylabel=f'{ylabel_prefix} Reduction (%)', legend=False)
    ax.legend(loc='upper left', edgecolor='black', fontsize=10)

    all_y_data = [line.get_ydata() for line in ax.lines]
    if all_y_data:
        max_y = max(max(y) for y in all_y_data)
        min_y = min(min(y) for y in all_y_data)
        ax.set_ylim(min_y - 5, max_y + 15)

    plt.tight_layout()
    fig.savefig(f'{OUT_THESIS}/{filename}.png', dpi=300, bbox_inches='tight')
    plt.close(fig)

def plot_presentation_dual_axis_sweep(filename):
    """
    Directly incorporates the specialized dual-axis continuous curve logic
    from PresentationCandE.py for exact presentation formatting.
    """
    voltages = np.array([300, 600, 900, 1200, 1500])
    si_coer = np.array([1.2517, 0.8128, 0.6400, 0.5796, 0.5516])
    sap_coer = np.array([1.0116, 0.5841, 0.4741, 0.4371, 0.4187])
    si_eoer = np.array([56.3273, 146.3069, 259.2202, 417.2925, 620.5282])
    sap_eoer = np.array([45.5204, 105.1334, 192.0251, 313.6696, 470.0686])

    v_smooth = np.linspace(300, 1500, 300)
    spl_si_c = make_interp_spline(voltages, si_coer, k=2)
    spl_sap_c = make_interp_spline(voltages, sap_coer, k=2)
    spl_si_e = make_interp_spline(voltages, si_eoer, k=2)
    spl_sap_e = make_interp_spline(voltages, sap_eoer, k=2)

    fig, ax1 = plt.subplots(figsize=(6, 4.5))

    color_c = '#333333'
    ax1.set_xlabel(r'Drain Voltage $V_{ds}$ (V)', fontweight='bold')
    ax1.set_ylabel(r'Equivalent Capacitance $C_{o(er)}$ (pF/mm)', color=color_c, fontweight='bold')
    l1 = ax1.plot(v_smooth, spl_si_c(v_smooth), linestyle='--', linewidth=2.5, color='#E63946', label=r'Silicon $C_{o(er)}$')
    l2 = ax1.plot(v_smooth, spl_sap_c(v_smooth), linestyle='--', linewidth=2.5, color='#0096C7', label=r'Sapphire $C_{o(er)}$')
    ax1.tick_params(axis='y', labelcolor=color_c)
    ax1.set_ylim(0, 1.6) 
    ax1.set_xlim(300, 1500)
    ax1.set_xticks([300, 600, 900, 1200, 1500])
    ax1.grid(True, linestyle=':', alpha=0.6)

    ax2 = ax1.twinx()  
    color_e = '#000000'
    ax2.set_ylabel(r'Stored Energy $E_{o(er)}$ (nJ/mm)', color=color_e, fontweight='bold')  
    l3 = ax2.plot(v_smooth, spl_si_e(v_smooth), linestyle='-', linewidth=3, color='#E63946', label=r'Silicon $E_{o(er)}$')
    l4 = ax2.plot(v_smooth, spl_sap_e(v_smooth), linestyle='-', linewidth=3, color='#0096C7', label=r'Sapphire $E_{o(er)}$')
    ax2.tick_params(axis='y', labelcolor=color_e)
    ax2.set_ylim(0, 800)

    lines = l1 + l2 + l3 + l4
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, 1.18), ncol=2, frameon=True, edgecolor='black')

    plt.tight_layout()
    fig.savefig(f'{OUT_THESIS}/{filename}.png', dpi=300, bbox_inches='tight')
    plt.close(fig)

# Execution
plot_dielectric_scaling('Coer_App1_DielectricScaling')
plot_approach_5('Coer', r'$C_{o(er)}$', 'Coer_App5_ReductionPercentage')
plot_presentation_dual_axis_sweep('Dual_Axis_Sweep_Coer')

print("All tasks completed successfully. Final outputs saved in Results/Capacitance/.")