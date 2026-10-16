# Nordic BESS Revenue Stack

**Question:** how much can a 10 MW battery in SE3 earn from day-ahead arbitrage plus FCR-D and FCR-N reserves, and how much does the answer depend on the assumptions?

**Status:** v0.1. Dispatch optimiser and revenue stack are built and tested. Forecasting and the finance layer are not started.

## Scope

In scope (v0.1):
- Day-ahead arbitrage, FCR-D and FCR-N reserves, co-optimised in one dispatch model
- Hourly resolution, SoC carried between days
- Daily and annual revenue outputs, with revenue split by product
- Synthetic demo prices, and a loader for real hourly CSVs

Out of scope (later):
- Price forecasting (v0.1 assumes perfect foresight within each day, so it is an upper bound)
- Project finance: debt sizing, DSCR, equity IRR
- Degradation, grid charges, intraday trading

## Method

Exact dynamic programming over a discretised state-of-charge grid. Each hour, the model chooses day-ahead power, FCR-D reserve, and FCR-N reserve, subject to:
- rated power: reserves plus absolute dispatch fit inside P
- SoC: must cover a full 15-minute reserve activation and leave room for one (assumption, set in `asset.py`)

The optimiser uses NumPy only. The original plan was an LP solver (HiGHS via SciPy), but pip is blocked on the machine this was built on. The LP version can be added once SciPy is available. It should give the same answers, and the tests check that.

## Run it

```
cd "08 Nordic BESS Revenue Stack"
PYTHONPATH=src python3 -m bess_stack                     # synthetic demo prices
PYTHONPATH=src python3 -m bess_stack --csv data/se3.csv  # real hourly data
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Output: a summary on the console, and a daily CSV in `outputs/`.

## Known limitations

- **Perfect foresight:** results are an upper bound, not a forecast-based strategy.
- **SoC rounding:** SoC snaps to a 0.5 MWh grid each hour. With efficiency below 1 this adds a small error.
- **Terminal value:** stored energy at the end of each day is valued at zero, so the battery has no incentive to end the day charged. This biases daily results slightly.
- **Symmetric FCR:** FCR-D and FCR-N are modelled as symmetric up and down reserves.
- **Assumed parameters:** efficiency 92% each way, 15-minute activation, no cycle cost by default.

## Next steps

1. Build the SE3 CSV from the ENTSO-E and Svenska kraftnät sources in `data/README.md`
2. Calibrate the baseline against 2023–2025 and report the FCR-D price compression effect
3. Add a day-ahead price forecast and compare forecast-based revenue with the perfect-foresight upper bound
4. Add the LP solver once SciPy is available
5. Add the finance layer (debt, DSCR, equity IRR) as a separate module
6. Compare revenue per MW-year with the Modo GB benchmark as a sanity check
