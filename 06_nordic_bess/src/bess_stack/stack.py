"""Run the optimiser day by day, carrying SoC from one day to the next."""

import csv
import os

import numpy as np

from .asset import BatteryAsset
from .optimizer import DayPrices, optimise_day

FIELDS = [
    "day", "start_soc_mwh", "end_soc_mwh", "revenue_da_eur", "revenue_fcr_d_eur",
    "revenue_fcr_n_eur", "cycle_cost_eur", "net_revenue_eur", "throughput_mwh",
    "fcr_d_mw_avg", "fcr_n_mw_avg",
]


def run_horizon(asset, da, fcr_d, fcr_n, hours_per_day=24, power_step=1.0, soc_step=0.5):
    da, fcr_d, fcr_n = np.asarray(da, float), np.asarray(fcr_d, float), np.asarray(fcr_n, float)
    n_days = len(da) // hours_per_day
    if n_days == 0:
        raise ValueError("need at least one full day of prices")
    soc = asset.soc0_frac * asset.energy_mwh
    rows = []
    for d in range(n_days):
        sl = slice(d * hours_per_day, (d + 1) * hours_per_day)
        res = optimise_day(
            asset, DayPrices(da[sl], fcr_d[sl], fcr_n[sl]), soc, power_step, soc_step
        )
        rows.append({
            "day": d + 1,
            "start_soc_mwh": round(float(res.soc[0]), 3),
            "end_soc_mwh": round(float(res.soc[-1]), 3),
            "revenue_da_eur": round(res.revenue_da, 2),
            "revenue_fcr_d_eur": round(res.revenue_fcr_d, 2),
            "revenue_fcr_n_eur": round(res.revenue_fcr_n, 2),
            "cycle_cost_eur": round(res.cycle_cost, 2),
            "net_revenue_eur": round(res.revenue, 2),
            "throughput_mwh": round(res.throughput_mwh, 3),
            "fcr_d_mw_avg": round(float(res.r_fcr_d.mean()), 3),
            "fcr_n_mw_avg": round(float(res.r_fcr_n.mean()), 3),
        })
        soc = res.soc[-1]
    return rows


def summarise(rows, asset):
    days = len(rows)
    total = sum(r["net_revenue_eur"] for r in rows)
    per_mw_year = total / asset.power_mw * 365.0 / days
    return {
        "days": days,
        "net_revenue_eur": round(total, 2),
        "revenue_per_mw_year_eur": round(per_mw_year, 0),
        "da_share": round(sum(r["revenue_da_eur"] for r in rows) / total, 3) if total else 0.0,
        "fcr_d_share": round(sum(r["revenue_fcr_d_eur"] for r in rows) / total, 3) if total else 0.0,
        "fcr_n_share": round(sum(r["revenue_fcr_n_eur"] for r in rows) / total, 3) if total else 0.0,
        "throughput_mwh": round(sum(r["throughput_mwh"] for r in rows), 1),
    }


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
