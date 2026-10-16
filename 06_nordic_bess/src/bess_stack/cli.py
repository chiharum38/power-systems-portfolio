import argparse

from .asset import BatteryAsset
from .markets import load_prices_csv, synthetic_prices
from .stack import run_horizon, summarise, write_csv


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="bess_stack",
        description="Nordic BESS revenue stack: day-ahead arbitrage plus FCR-D and FCR-N. "
                    "Perfect foresight within each day.",
    )
    ap.add_argument("--csv", help="merged hourly price CSV (see data/README.md). "
                                  "Omit to run on synthetic demo prices.")
    ap.add_argument("--power", type=float, default=10.0, help="rated power, MW")
    ap.add_argument("--duration", type=float, default=2.0, help="hours at rated power")
    ap.add_argument("--soc0", type=float, default=0.5, help="starting SoC as a fraction")
    ap.add_argument("--eta", type=float, default=0.92, help="one-way efficiency")
    ap.add_argument("--cycle-cost", type=float, default=0.0, help="EUR per MWh throughput")
    ap.add_argument("--out", default="outputs/daily_results.csv", help="daily results CSV")
    args = ap.parse_args(argv)

    asset = BatteryAsset(
        power_mw=args.power,
        energy_mwh=args.power * args.duration,
        eta_charge=args.eta,
        eta_discharge=args.eta,
        soc0_frac=args.soc0,
        cycle_cost_eur_mwh=args.cycle_cost,
    )
    series = load_prices_csv(args.csv) if args.csv else synthetic_prices()
    rows = run_horizon(asset, series.da, series.fcr_d, series.fcr_n)
    s = summarise(rows, asset)
    write_csv(rows, args.out)

    print(f"Source:               {series.source}")
    print(f"Asset:                {args.power:g} MW / {asset.energy_mwh:g} MWh")
    print(f"Days simulated:       {s['days']}")
    print(f"Net revenue:          EUR {s['net_revenue_eur']:,.0f}")
    print(f"Revenue per MW-year:  EUR {s['revenue_per_mw_year_eur']:,.0f}")
    print(f"Revenue split:        DA {s['da_share']:.0%}, FCR-D {s['fcr_d_share']:.0%}, "
          f"FCR-N {s['fcr_n_share']:.0%}")
    print(f"Throughput:           {s['throughput_mwh']:,.1f} MWh")
    print(f"Daily results:        {args.out}")
    return 0
