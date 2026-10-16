import itertools
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bess_stack.asset import BatteryAsset  # noqa: E402
from bess_stack.markets import load_prices_csv, synthetic_prices  # noqa: E402
from bess_stack.optimizer import DayPrices, optimise_day  # noqa: E402
from bess_stack.stack import run_horizon  # noqa: E402


def lossless_asset(power=2.0, energy=2.0, **kw):
    # eta = 1 and activation = 1 h keep every SoC on the integer grid, so the
    # DP can be checked exactly against brute-force enumeration.
    return BatteryAsset(power_mw=power, energy_mwh=energy, eta_charge=1.0,
                        eta_discharge=1.0, soc0_frac=0.5, activation_hours=1.0, **kw)


def brute_force_value(asset, prices, soc0):
    P = int(asset.power_mw)
    actions = [(p, rd, rn)
               for p in range(-P, P + 1)
               for rd in range(0, P + 1)
               for rn in range(0, P + 1)
               if rd + rn + abs(p) <= asset.power_mw]
    best = [-np.inf]

    def rec(t, soc, acc):
        if t == len(prices.da):
            best[0] = max(best[0], acc)
            return
        for p, rd, rn in actions:
            r = rd + rn
            lo = r * asset.activation_hours
            hi = asset.energy_mwh - lo
            nxt = soc - p          # eta = 1: discharge p removes p MWh
            if lo - 1e-9 <= nxt <= hi + 1e-9:
                rev = p * prices.da[t] + rd * prices.fcr_d[t] + rn * prices.fcr_n[t]
                rec(t + 1, nxt, acc + rev)

    rec(0, soc0, 0.0)
    return best[0]


class TestOptimiser(unittest.TestCase):

    def test_matches_brute_force(self):
        asset = lossless_asset()
        rng = np.random.default_rng(1)
        for _ in range(3):
            prices = DayPrices(
                da=rng.integers(-10, 60, 3).astype(float),
                fcr_d=rng.integers(0, 30, 3).astype(float),
                fcr_n=rng.integers(0, 30, 3).astype(float),
            )
            res = optimise_day(asset, prices, soc_start_mwh=1.0, power_step=1.0, soc_step=1.0)
            self.assertAlmostEqual(res.value, brute_force_value(asset, prices, 1.0), places=6)

    def test_value_equals_schedule_revenue(self):
        asset = BatteryAsset(power_mw=10, energy_mwh=20, cycle_cost_eur_mwh=2.0)
        series = synthetic_prices(days=1, seed=3)
        res = optimise_day(asset, DayPrices(series.da[:24], series.fcr_d[:24], series.fcr_n[:24]),
                           soc_start_mwh=10.0)
        self.assertAlmostEqual(res.value, res.revenue, places=3)

    def test_arbitrage_charges_low_and_discharges_high(self):
        asset = BatteryAsset(power_mw=5, energy_mwh=10, soc0_frac=0.0)
        da = np.array([5.0, 200.0])
        z = np.zeros(2)
        res = optimise_day(asset, DayPrices(da, z, z), soc_start_mwh=0.0)
        self.assertLess(res.p_da[0], 0.0)   # charge when cheap
        self.assertGreater(res.p_da[1], 0.0)  # discharge when expensive

    def test_reserves_chosen_when_only_fcr_pays(self):
        asset = BatteryAsset(power_mw=10, energy_mwh=20)
        z = np.zeros(24)
        res = optimise_day(asset, DayPrices(z, np.full(24, 50.0), z), soc_start_mwh=10.0)
        self.assertGreater(res.r_fcr_d.sum(), 0.0)
        self.assertGreater(res.revenue_fcr_d, 0.0)

    def test_constraints_hold_every_hour(self):
        asset = BatteryAsset(power_mw=10, energy_mwh=20)
        s = synthetic_prices(days=1, seed=7)
        res = optimise_day(asset, DayPrices(s.da[:24], s.fcr_d[:24], s.fcr_n[:24]),
                           soc_start_mwh=10.0)
        reserve = res.r_fcr_d + res.r_fcr_n
        self.assertTrue(np.all(reserve + np.abs(res.p_da) <= asset.power_mw + 1e-9))
        self.assertTrue(np.all(res.soc >= -1e-9))
        self.assertTrue(np.all(res.soc <= asset.energy_mwh + 1e-9))
        # SoC must cover a full activation of the reserve in every hour
        self.assertTrue(np.all(res.soc[:-1] >= reserve * asset.activation_hours - 1e-6))

    def test_non_dividing_power_step_rejected(self):
        asset = BatteryAsset(power_mw=10, energy_mwh=20)
        z = np.zeros(2)
        with self.assertRaises(ValueError):
            optimise_day(asset, DayPrices(z, z, z), 10.0, power_step=3.0)

    def test_revenue_not_negative_with_no_cost(self):
        asset = BatteryAsset(power_mw=10, energy_mwh=20)
        s = synthetic_prices(days=1, seed=11)
        res = optimise_day(asset, DayPrices(s.da[:24], s.fcr_d[:24], s.fcr_n[:24]),
                           soc_start_mwh=10.0)
        self.assertGreaterEqual(res.revenue, -1e-9)


class TestHorizonAndIO(unittest.TestCase):

    def test_multi_day_soc_carries_over(self):
        asset = BatteryAsset(power_mw=10, energy_mwh=20)
        s = synthetic_prices(days=3, seed=5)
        rows = run_horizon(asset, s.da, s.fcr_d, s.fcr_n)
        self.assertEqual(len(rows), 3)
        for prev, nxt in zip(rows, rows[1:]):
            self.assertAlmostEqual(prev["end_soc_mwh"], nxt["start_soc_mwh"], places=2)

    def test_csv_loader_rejects_missing_columns(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("timestamp,da_eur_mwh\n2026-01-01T00:00,40\n")
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_prices_csv(path)
        finally:
            os.unlink(path)

    def test_csv_loader_reads_valid_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("timestamp,da_eur_mwh,fcr_d_eur_mw_h,fcr_n_eur_mw_h\n"
                    "2026-01-01T00:00,40,6,4\n2026-01-01T01:00,42,6,4\n")
            path = f.name
        try:
            series = load_prices_csv(path)
            self.assertEqual(len(series.da), 2)
            self.assertEqual(series.da[1], 42.0)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
