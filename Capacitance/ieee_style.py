"""
ieee_style.py
=============
Shared IEEE publication-quality style for all thesis plotting scripts.
Import at the top of every script:
    from ieee_style import apply_ieee_style, COLORS, BUF_COLORS, LGD_COLORS,
                           SUB_COLORS, BUF_MARKERS, SUB_MARKERS, LGD_MARKERS,
                           BUF_LINESTYLES, save_fig, clean_ax
"""
import matplotlib as mpl
import matplotlib.pyplot as plt

def apply_ieee_style():
    mpl.rcParams.update({
        'font.family':          'serif',
        'font.serif':           ['Times New Roman', 'DejaVu Serif', 'serif'],
        'font.size':            9,
        'axes.labelsize':       10,
        'axes.titlesize':       9,
        'xtick.labelsize':      9,
        'ytick.labelsize':      9,
        'legend.fontsize':      8,
        'lines.linewidth':      2.0,
        'lines.markersize':     5,
        'axes.linewidth':       0.8,
        'axes.spines.top':      False,
        'axes.spines.right':    False,
        'axes.grid':            True,
        'grid.linestyle':       '--',
        'grid.linewidth':       0.5,
        'grid.alpha':           0.4,
        'grid.color':           '#999999',
        'xtick.direction':      'in',
        'ytick.direction':      'in',
        'legend.framealpha':    0.85,
        'legend.edgecolor':     '#CCCCCC',
        'legend.frameon':       True,
        'figure.dpi':           150,
        'savefig.dpi':          600,
        'savefig.bbox':         'tight',
        'savefig.pad_inches':   0.05,
        'figure.facecolor':     'white',
        'axes.facecolor':       'white',
    })

# Grayscale-safe palette (Wong color-blind safe palette)
COLORS = ['#0072B2','#D55E00','#009E73','#E69F00','#56B4E9','#CC79A7','#F0E442','#000000']

LGD_COLORS  = {10.0: '#0072B2', 15.0: '#D55E00', 20.0: '#009E73'}
BUF_COLORS  = {0.5:  '#0072B2',  5.0: '#D55E00'}
SUB_COLORS  = {5.0:  '#0072B2', 50.0: '#D55E00', 500.0: '#009E73'}

LGD_MARKERS = {10.0: 'o', 15.0: 's', 20.0: '^'}
BUF_MARKERS = {0.5:  'o',  5.0: 's'}
SUB_MARKERS = {5.0:  'o', 50.0: 's', 500.0: '^'}

BUF_LINESTYLES = {0.5: '-', 5.0: '--'}
SUB_LINESTYLES = {5.0: '-', 50.0: '--', 500.0: ':'}

def save_fig(fig, path, close=True):
    fig.savefig(path, dpi=600, bbox_inches='tight', pad_inches=0.05)
    if close:
        plt.close(fig)

def clean_ax(ax, xlabel, ylabel, legend=True, legend_loc='best', log_y=False, log_x=False):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if log_y: ax.set_yscale('log')
    if log_x: ax.set_xscale('log')
    if legend: ax.legend(loc=legend_loc, borderpad=0.6, labelspacing=0.4)
    ax.tick_params(which='both', direction='in')
