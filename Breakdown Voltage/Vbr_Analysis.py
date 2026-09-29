#!/usr/bin/env python3
"""
Vbr_Analysis.py - Cleaned IEEE thesis quality
Outputs (in Results/Comparisons/Breakdown_Trends/):
  - Vbr_vs_Lgd Trend Lines
  - Vbr Bar Charts (vs Lgd, Buffer, Substrate)
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import os, glob, re
from ieee_style import (apply_ieee_style, clean_ax)

# IEEE Publication Strict Settings
apply_ieee_style()
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman']
mpl.rcParams['mathtext.fontset'] = 'stix'  
mpl.rcParams['font.size'] = 10
mpl.rcParams['axes.labelsize'] = 10
mpl.rcParams['legend.fontsize'] = 9  
mpl.rcParams['xtick.labelsize'] = 9
mpl.rcParams['ytick.labelsize'] = 9

LOGS_DIR = 'logs/*.log'
OUT_DIR = 'Results/Comparisons/Breakdown_Trends'
os.makedirs(OUT_DIR, exist_ok=True)

# ── 1. Visual Parameter Mappings ─────────────────────────────────────
C_SAP = {5.0: '#48CAE4', 50.0: '#0096C7', 500.0: '#023E8A'}
C_SI  = {5.0: '#FF758F', 50.0: '#E63946', 500.0: '#780000'}

# Bar Chart Colors
C_SI_BAR     = C_SI[50.0]  
C_SAP_BAR    = C_SAP[50.0] 
C_SAP_FP_BAR = C_SAP[500.0] 

SUBSTRATE_ALIASES = {'Saphhire':'Sapphire','Saphire':'Sapphire',
                     'Sapphhire':'Sapphire','Sic':'SiC','Silicone':'Silicon',
                     'Si':'Silicon'}

# ── 2. Parser & Data Loading ──────────────────────────────────────────────────
def read_log(filename):
    try:
        with open(filename, 'r') as fh:
            raw = fh.readlines()
        code_label = {}
        for line in raw:
            line = line.strip()
            if line.startswith('Q '):
                parts = line.split(None, 3)
                if len(parts) == 4:
                    code_label[parts[1]] = parts[3].strip('"')
        vd_code  = next((c for c,l in code_label.items() if 'drain voltage' in l.lower()),  None)
        
        if not vd_code: return None
        
        col_names, rows = [], []
        for line in raw:
            line = line.strip()
            if line.startswith('p '):
                for code in line.split()[2:]:
                    if code == vd_code: col_names.append('vdrain')
                    else:               col_names.append('skip')
            elif line.startswith('d '):
                rows.append([float(x) for x in line.split()[1:]])
        data = np.array(rows)
        return {n: data[:,i] for i,n in enumerate(col_names) if n != 'skip'}
    except Exception:
        return None

master_data = []
print(f"Scanning {LOGS_DIR} and extracting breakdown data...")

for fpath in glob.glob(LOGS_DIR):
    base = os.path.basename(fpath).replace('.log','')
    lgd_m = re.search(r'Lgd([\d.]+)',                         base, re.I)
    buf_m = re.search(r'Buffer_([\d._]+)um',                  base, re.I)
    sub_m = re.search(r'[Ss]ubstrate_([A-Za-z]+)_([\d._]+)um', base, re.I)
    fp_m  = re.search(r'gate_source_FP',                      base, re.I)
    
    if not (lgd_m and buf_m and sub_m):
        continue
        
    lgd     = float(lgd_m.group(1))
    buf     = float(buf_m.group(1).replace('_','.'))
    sub_raw = sub_m.group(1).capitalize()
    sub_type = SUBSTRATE_ALIASES.get(sub_raw, sub_raw)
    sub_thk = float(sub_m.group(2).replace('_','.'))
    fp_type = 'GS-FP' if fp_m else 'Std'

    cols = read_log(fpath)
    if cols is None or 'vdrain' not in cols:
        continue

    vd = cols['vdrain']
    valid = np.where(vd > 10)[0] # Filter out noise logs
    if len(valid) < 2:
        continue
        
    vbr = float(np.max(vd[valid]))
    
    # Store only scalar values to save massive amounts of memory
    master_data.append({'vbr': vbr, 'lgd': lgd, 'buf': buf, 
                        'sub_type': sub_type, 'sub_thk': sub_thk, 'fp': fp_type})

print(f"Loaded {len(master_data)} devices.\n")

def get_max_vbr(mat, fp, lgd=None, buf=None, sub_thk=None):
    vals = []
    for d in master_data:
        if d['sub_type'] != mat or d['fp'] != fp:
            continue
        if lgd is not None and d['lgd'] != lgd:
            continue
        if buf is not None and d['buf'] != buf:
            continue
        if sub_thk is not None and d['sub_thk'] != sub_thk:
            continue
        if not np.isnan(d['vbr']):
            vals.append(d['vbr'])
    return max(vals) if vals else 0.0


# ── 3. Bar Chart & Trend Master Loop ──────────────────────────────────────────
def autolabel(rects, ax):
    for rect in rects:
        height = rect.get_height()
        if height > 0:
            ax.annotate(f'{int(height)}', xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=12)

def format_barchart(fig, ax, x, tick_labels, xlabel, save_path):
    ax.axhline(1200, color='black', linestyle='--', linewidth=1.5, label='1200 V Target')
    ax.set_xticks(x); ax.set_xticklabels(tick_labels)
    clean_ax(ax, xlabel=xlabel, ylabel=r'Max Breakdown Voltage $V_{br}$ (V)', legend=False)
    
    # Re-integrated inside legend
    ax.legend(loc='upper left', edgecolor='black', fontsize=9)
    
    fig.subplots_adjust(bottom=0.15)
    fig.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

groupings = {
    "1_Silicon": [('Silicon', 'Std', C_SI_BAR, '', 's')],
    "2_Sapphire": [('Sapphire', 'Std', C_SAP_BAR, '', 'o')],
    "3_Si_Sap": [('Silicon', 'Std', C_SI_BAR, '', 's'), 
                 ('Sapphire', 'Std', C_SAP_BAR, '', 'o')],
    "4_Si_Sap_FP": [('Silicon', 'Std', C_SI_BAR, '', 's'), 
                    ('Sapphire', 'Std', C_SAP_BAR, '', 'o'), 
                    ('Sapphire', 'GS-FP', C_SAP_FP_BAR, '//', '^')]
}

print("Generating Vbr Bar Charts and Vbr vs Lgd Trend Lines...")

for group_name, categories in groupings.items():
    if len(categories) == 1:   w = 0.4
    elif len(categories) == 2: w = 0.3
    else:                      w = 0.25
    
    lgds = [10.0, 15.0, 20.0]
    x = np.arange(len(lgds))
    
    # A. Generate Bar Charts for this Stage
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for i, (mat, fp, col, hatch, _) in enumerate(categories):
        vals = [get_max_vbr(mat, fp, lgd=l) for l in lgds]
        offset = (i - len(categories)/2 + 0.5) * w
        r = ax.bar(x + offset, vals, w, label=f"{mat} ({fp})", color=col, hatch=hatch, edgecolor='black')
        autolabel(r, ax)
    format_barchart(fig, ax, x, [f"{int(l)}" for l in lgds], r'Gate-to-Drain Spacing $L_{gd}$ (µm)', 
                    f"{OUT_DIR}/Vbr_BarChart_{group_name}_vs_Lgd.png")

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    x_buf = np.arange(2)
    bufs = [0.5, 5.0]
    for i, (mat, fp, col, hatch, _) in enumerate(categories):
        vals = [get_max_vbr(mat, fp, buf=b) for b in bufs]
        offset = (i - len(categories)/2 + 0.5) * w
        r = ax.bar(x_buf + offset, vals, w, label=f"{mat} ({fp})", color=col, hatch=hatch, edgecolor='black')
        autolabel(r, ax)
    format_barchart(fig, ax, x_buf, [f"{b}" for b in bufs], r'Buffer Thickness $t_{buf}$ (µm)', 
                    f"{OUT_DIR}/Vbr_BarChart_{group_name}_vs_Buffer.png")

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    x_sub = np.arange(3)
    subs = [5.0, 50.0, 500.0]
    for i, (mat, fp, col, hatch, _) in enumerate(categories):
        vals = [get_max_vbr(mat, fp, sub_thk=s) for s in subs]
        offset = (i - len(categories)/2 + 0.5) * w
        r = ax.bar(x_sub + offset, vals, w, label=f"{mat} ({fp})", color=col, hatch=hatch, edgecolor='black')
        autolabel(r, ax)
    format_barchart(fig, ax, x_sub, [f"{s}" for s in subs], r'Substrate Thickness $t_{sub}$ (µm)', 
                    f"{OUT_DIR}/Vbr_BarChart_{group_name}_vs_Substrate.png")

    # B. Generate Trend Line for this Stage
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    max_val_found = 1200
    for mat, fp, col, hatch, marker in categories:
        vals = [get_max_vbr(mat, fp, lgd=l) for l in lgds]
        if any(v > 0 for v in vals): max_val_found = max(max_val_found, max(vals))
        ls = '--' if mat == 'Silicon' else '-'
        ax.plot(lgds, vals, marker=marker, markersize=7, linestyle=ls, linewidth=2, color=col, label=f"{mat} ({fp})")

    ax.axhline(1200, color='black', linestyle=':', linewidth=1.5, label='1200 V Target')
    clean_ax(ax, xlabel=r'Gate-to-Drain Spacing $L_{gd}$ (µm)', ylabel=r'Maximum Breakdown Voltage $V_{br}$ (V)', legend=False)
    ax.yaxis.set_major_formatter(plt.ScalarFormatter())
    
    # Establish a strictly linear x-axis from 10 to 20 with increments of 1
    ax.set_xlim(9.5, 20.5)
    ax.set_xticks(np.arange(10, 21, 1))
    
    # Draw the axis break ("kink") at the start of the x-axis (bottom-left)
    d = 0.015  # Size of the diagonal lines
    kwargs = dict(transform=ax.transAxes, color='black', clip_on=False, linewidth=1.5)
    ax.plot([-d, d], [-d, d], **kwargs)
    ax.plot([-d + 0.02, d + 0.02], [-d, d], **kwargs)
    
    ax.set_ylim(0, max_val_found * 1.15) 
    ax.grid(True, linestyle='--', alpha=0.5)
    
    # Re-integrated inside legend
    ax.legend(loc='lower right', edgecolor='black', fontsize=9)
    
    fig.subplots_adjust(bottom=0.15)
    fig.savefig(f"{OUT_DIR}/Vbr_vs_Lgd_Trend_IEEE_{group_name}.png", dpi=300, bbox_inches='tight')
    plt.close(fig)

print("All tasks completed.")