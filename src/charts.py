"""Article figure: large-hail trend and 2030 projection (left), hazard vs damage column indexed (right). Turkish labels."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from climate import rate

BLUE, ORANGE, INK, MUTED = "#2A5DB0", "#D9661F", "#1d1d1f", "#6b6b70"


def figure(res: dict, art: dict, path: Path) -> None:
    plt.rcParams.update({"font.family": "Calibri", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.9), dpi=200)

    # left: large-hail reports, trend to 2030, 80% predictive interval, flat 30-year mean
    h = art["big_hail"]
    a.plot(h.index, h.values, color=BLUE, lw=2, marker="o", ms=3.5, label="Gözlenen (≥ 5 cm dolu raporu)")
    yrs = np.arange(1996, 2031)
    a.plot(yrs, rate(res["large_hail"]["trend"], yrs), color=ORANGE, lw=2, label="Trend modeli")
    a.axhline(res["large_hail"]["mean_1996_2025"], color=MUTED, lw=1, ls="--")
    a.text(1997, res["large_hail"]["mean_1996_2025"] + 25, "30 yıllık ortalama", color=MUTED, fontsize=8)
    lo, hi = res["projection_2030"]["pi80"]
    a.errorbar([2030], [res["projection_2030"]["mean"]], yerr=[[res["projection_2030"]["mean"] - lo], [hi - res["projection_2030"]["mean"]]],
               fmt="o", color=ORANGE, ms=6, capsize=4, lw=1.5)
    a.text(2029.6, hi + 30, "2030\n(%80 aralık)", color=INK, fontsize=8, ha="center")
    a.set(xlim=(1995, 2032), ylim=(0, 1700), ylabel="Yıllık rapor sayısı")
    a.set_title("Büyük dolu artıyor", color=INK, fontsize=10, loc="left")
    a.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, 0.93))
    a.grid(alpha=0.25, lw=0.5)

    # right: hazard vs damage column, indexed 1996-2005 = 100
    base_h, base_d = h.loc[:2005].mean(), art["big_dmg"].loc[:2005].mean()
    roll = lambda s: s.rolling(3, center=True, min_periods=2).mean()
    ih, idm = roll(h / base_h * 100), roll(art["big_dmg"] / base_d * 100)
    b.plot(ih.index, ih.values, color=BLUE, lw=2)
    b.plot(idm.index, idm.values, color=ORANGE, lw=2)
    b.axhline(100, color=MUTED, lw=1, ls="--")
    b.text(2025.6, ih.iloc[-1], "Büyük dolu\n(tehlike)", color=INK, fontsize=8, va="center")
    b.text(2025.6, idm.iloc[-1], "10 milyon $ üstü\nkayıtlı hasar", color=INK, fontsize=8, va="center")
    b.set(xlim=(1995, 2031), ylim=(0, 230), ylabel="Endeks (1996–2005 = 100, 3 yıllık ort.)")
    b.set_title("Tehlike büyürken hasar kaydı küçülüyor", color=INK, fontsize=10, loc="left")
    b.grid(alpha=0.25, lw=0.5)

    fig.tight_layout(w_pad=2.5)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
