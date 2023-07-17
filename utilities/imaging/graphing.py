from __future__ import annotations

import re
from io import BytesIO
from statistics import StatisticsError, mean, mode, quantiles
from typing import TYPE_CHECKING

import matplotlib
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.font_manager import FontProperties
from sympy import lambdify, symbols, sympify

import discord
from core import Context
from utilities.converters import ToAsync as to_thread

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

matplotlib.use('agg')
plt.style.use(('bmh', 'ggplot'))  # type: ignore
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
def plotfn(_: Context, equation: str, *, xrange: tuple[int, int] = (-20, 20)) -> discord.File:
    x = symbols('x')
    equation = _clean_implicit_mul(equation)
    expr = sympify(equation)  # Convert equation string to a Sympy expression
    print(expr)
    func = lambdify(x, expr)  # Create a function from the Sympy expression

    x_vals = np.linspace(*xrange, 500)
    y_vals = func(x_vals)  # Evaluate the function for the x-values

    plt.plot(x_vals, y_vals)
    plt.xlabel('X - Axis')
    plt.ylabel('Y - Axis')
    plt.title(f'Graph of {equation}')
    plt.grid(True)
    plt.axhline(0, color='black', linewidth=0.5)
    plt.axvline(0, color='black', linewidth=0.5)

    plt.annotate(
        "Created by Parrot Bot",
        xy=(0.999, 0.01),
        xycoords='axes fraction',
        fontsize=8,
        horizontalalignment='right',
        verticalalignment='bottom',
        bbox={"facecolor": "orange", "alpha": 0.5, "pad": 5},
    )
    image_buffer = BytesIO()
    plt.savefig(image_buffer, format='png')
    image_buffer.seek(0)

    plt.close()

    return discord.File(image_buffer, 'graph.png')
