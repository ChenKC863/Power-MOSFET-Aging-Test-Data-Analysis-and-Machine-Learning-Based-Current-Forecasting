"""Export the case-study time series as white-background JPEG figures."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE / 'output'
OUT.mkdir(exist_ok=True)
data = json.loads((HERE / 'slide_data.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12,
                     'figure.facecolor': 'white', 'axes.facecolor': 'white',
                     'text.color': '#102E50', 'axes.labelcolor': '#102E50',
                     'xtick.color': '#102E50', 'ytick.color': '#102E50'})

def draw(ax, case):
    summary = case['summary']
    x = np.arange(len(case['labels']))
    for field, label, color in [('target','Observed','#152F45'),
                                 ('persistence','Persistence','#C28A25'),
                                 ('prediction','Ridge','#1375AE')]:
        y = np.array([np.nan if v is None else v for v in case['series'][field]])
        ax.plot(x, y, label=label, color=color, linewidth=1.8)
    is27 = summary['group'] == 'Test_27'
    ax.set_ylim((1.68, 1.80) if is27 else (1.70, 2.50))
    ax.set_yticks([1.68, 1.72, 1.76, 1.80] if is27 else [1.7,1.9,2.1,2.3,2.5])
    ax.set_xlim(0, len(x)-1)
    ax.set_xticks(np.arange(0, len(x), 10 if is27 else 20))
    ax.set_xlabel(f"Minutes after {case['labels'][0]} (target-minute end)", labelpad=10)
    ax.set_ylabel('Mean current (recorded scale)', labelpad=10)
    ax.grid(axis='y', color='#DEDEDE', linewidth=.7)
    ax.set_axisbelow(True)
    for k in ['top','right']: ax.spines[k].set_visible(False)
    for k in ['left','bottom']: ax.spines[k].set_color('#AAAAAA')
    ax.legend(loc='lower center', bbox_to_anchor=(.5,1.01), ncol=3,
              frameon=False, handlelength=2.2, columnspacing=1.6)

for case in data:
    fig, ax = plt.subplots(figsize=(9,4.1), layout='constrained')
    draw(ax,case)
    name = case['summary']['group'] + '_forecast_comparison_white.jpg'
    fig.savefig(OUT/name, dpi=300, facecolor='white', pil_kwargs={'quality':98,'subsampling':0})
    plt.close(fig)
    print(OUT/name)

fig, axes = plt.subplots(1,2,figsize=(16,4.6),layout='constrained')
for ax,case in zip(axes,data):
    draw(ax,case)
    s=case['summary']
    ax.set_title(s['file']+'   '+s['peak_target_start'][:10],fontsize=13,pad=48,fontweight='bold')
fig.savefig(OUT/'Engineering_cases_white.jpg',dpi=300,facecolor='white',pil_kwargs={'quality':98,'subsampling':0})
plt.close(fig)
print(OUT/'Engineering_cases_white.jpg')
