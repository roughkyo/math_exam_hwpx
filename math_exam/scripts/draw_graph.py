"""다항식 그래프의 선·음영만 그립니다. 표기는 HWPX 수식으로 따로 배치합니다."""
from pathlib import Path
import argparse
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def draw(spec, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    width, height = spec.get('size', [290, 220])
    fig = plt.figure(figsize=(width / 100, height / 100), dpi=240)
    ax = fig.add_axes([.08, .09, .83, .8])
    ax.set_xlim(*spec['xlim'])
    ax.set_ylim(*spec['ylim'])
    ax.axis('off')
    ax.annotate('', xy=(spec['xlim'][1], 0), xytext=(spec['xlim'][0], 0), arrowprops={'arrowstyle': '->', 'lw': .7})
    ax.annotate('', xy=(0, spec['ylim'][1]), xytext=(0, spec['ylim'][0]), arrowprops={'arrowstyle': '->', 'lw': .7})
    x = np.linspace(*spec['xlim'], 900)
    curves = spec['curves']
    for coefficients in curves:
        ax.plot(x, np.polyval(coefficients, x), color='black', lw=1)
    for interval in spec.get('shade', []):
        t = np.linspace(*interval, 400)
        ax.fill_between(t, np.polyval(curves[0], t), np.polyval(curves[1], t), color='.83')
    for a, b in spec.get('verticals', []):
        ax.plot([a, a], [0, b], '--', color='.5', lw=.6)
    fig.savefig(output, format='png', facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('spec')
    p.add_argument('output')
    a = p.parse_args()
    draw(json.loads(Path(a.spec).read_text(encoding='utf-8')), a.output)
