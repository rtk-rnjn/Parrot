from __future__ import annotations

import re
import time
from io import BytesIO
from statistics import StatisticsError, mean, mode, quantiles
from typing import TYPE_CHECKING, Any

import matplotlib
import numpy as np

from core import Context

matplotlib.use('agg')

from matplotlib import pyplot as plt
from matplotlib.font_manager import FontProperties

plt.style.use(('bmh', 'ggplot'))  # type: ignore

from Equation import Expression

import discord
from utilities.converters import ToAsync as to_thread

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

__all__: tuple[str, ...] = (
    'boxplot',
    'plotfn',
)

CODEFONT: FontProperties = FontProperties(
    fname='extra/Monaco-Linux.ttf',  # type: ignore
)


@to_thread()
def boxplot(_, data: list[float], *, fill_boxes: bool = True) -> discord.File:
    fig: Figure = plt.figure()
    ax: Axes = fig.add_subplot()
    ax.set_title('Box & Whisker Plot', pad=15)

    out = ax.boxplot(
        x=data,
        vert=False,
        showmeans=True,
        labels=['A'],
        patch_artist=fill_boxes,
    )

    for cap in out.get('caps', ()):
        cap.set(color='#8B008B', linewidth=2)

    for whisk in out.get('whiskers', ()):
        whisk.set(color='#5043a9', linewidth=2)

    for box in out.get('boxes', ()):
        box.set(color='#71525b', linewidth=2)

    for median in out.get('medians', ()):
        median.set(color='#b54d6a', linewidth=2)

    x = ax.get_xticks()[1]

    _min, _max = min(data), max(data)
    ax.text(
        x,
        1.4,
        f'Min: {_min}',
        fontproperties=CODEFONT,
    )
    ax.text(
        x,
        1.34,
        f'Max: {_max}',
        fontproperties=CODEFONT,
    )
    ax.text(
        x,
        1.28,
        f'Range: {_max - _min}',
        fontproperties=CODEFONT,
    )
    ax.text(
        x,
        1.22,
        f'Mean: {mean(data)}',
        fontproperties=CODEFONT,
    )
    ax.text(
        x,
        1.16,
        f'Mode: {mode(data)}',
        fontproperties=CODEFONT,
    )

    try:
        q1, q2, q3 = quantiles(data, n=4)
    except StatisticsError:
        q1 = q2 = q3 = data[0]

    ax.text(
        x,
        0.8,
        f'Q1: {q1}',
        fontproperties=CODEFONT,
    )
    ax.text(
        x,
        0.74,
        f'Q2: {q2}',
        fontproperties=CODEFONT,
    )
    ax.text(
        x,
        0.68,
        f'Q3: {q3}',
        fontproperties=CODEFONT,
    )
    ax.text(
        x,
        0.62,
        f'IQR: {q3 - q1}',
        fontproperties=CODEFONT,
    )

    buffer = BytesIO()
    plt.savefig(buffer)
    plt.close()
    buffer.seek(0)
    return discord.File(buffer, 'graph.png')


def _clean_implicit_mul(equation: str) -> str:
    def _sub_mul(val: re.Match) -> str:
        parts = list(val.group())
        parts.insert(-1, '*')
        return ''.join(parts)

    equation = re.sub(r'\s+', '', equation)
    equation = re.sub(r'(?<=[0-9x)])x', _sub_mul, equation)
    equation = equation.replace(')(', ')*(')
    return equation


@to_thread()
def plotfn(_, equation: str, *, xrange: tuple[int, int] = (-20, 20)) -> discord.File:
    fig: Figure = plt.figure()
    ax: Axes = fig.add_subplot(1, 1, 1)
    ax.set_title(f'y = {equation}', pad=15)
    equation = _clean_implicit_mul(equation)

    fx = np.vectorize(Expression(equation, ['x']))
    x = np.linspace(*xrange, 1000)

    ax.set_aspect('equal', adjustable='box')
    ax.spines['left'].set_position('center')  # type: ignore
    ax.spines['bottom'].set_position('zero')  # type: ignore
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    ax.set_ylim(*ax.get_xlim())

    ax.plot(x, fx(x))
    plt.axis('equal')

    buffer = BytesIO()
    plt.savefig(buffer)
    plt.close()
    buffer.seek(0)
    return discord.File(buffer, 'graph.png')
