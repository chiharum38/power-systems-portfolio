"""Price inputs: a merged hourly CSV, or synthetic demo prices for testing."""

import csv
from dataclasses import dataclass

import numpy as np

REQUIRED_COLUMNS = ("timestamp", "da_eur_mwh", "fcr_d_eur_mw_h", "fcr_n_eur_mw_h")


@dataclass(frozen=True)
class PriceSeries:
    timestamps: list
    da: np.ndarray
    fcr_d: np.ndarray
    fcr_n: np.ndarray
    source: str


def load_prices_csv(path: str) -> PriceSeries:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path} has no data rows")
    return PriceSeries(
        timestamps=[r["timestamp"] for r in rows],
        da=np.array([float(r["da_eur_mwh"]) for r in rows]),
        fcr_d=np.array([float(r["fcr_d_eur_mw_h"]) for r in rows]),
        fcr_n=np.array([float(r["fcr_n_eur_mw_h"]) for r in rows]),
        source=path,
    )


def synthetic_prices(days: int = 7, seed: int = 0) -> PriceSeries:
    """Demo prices with a morning dip, an evening peak and noise. Not market data."""
    rng = np.random.default_rng(seed)
    h = np.arange(24 * days)
    hour = h % 24
    da = 35 + 20 * np.sin((hour - 6) / 24 * 2 * np.pi) + 15 * ((hour >= 17) & (hour <= 20))
    da = da + rng.normal(0, 6, size=h.size)
    fcr_d = np.clip(6 + 2 * np.sin(h / 24 * 2 * np.pi) + rng.normal(0, 1.5, h.size), 0, None)
    fcr_n = np.clip(4 + rng.normal(0, 1, h.size), 0, None)
    ts = [f"synthetic-day{i // 24 + 1:02d}-h{i % 24:02d}" for i in h]
    return PriceSeries(ts, da, fcr_d, fcr_n, source="synthetic demo prices (not market data)")
