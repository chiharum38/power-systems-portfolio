"""Dispatch optimiser for one battery over one day.

Method: exact dynamic programming over a discretised state-of-charge (SoC) grid.
Each hour the action is (day-ahead power, FCR-D reserve MW, FCR-N reserve MW).

Constraints per hour:
  * dispatch power is within [-P, P]
  * reserves plus absolute dispatch fit inside rated power: RD + RN + |p| <= P
  * after the hour, SoC covers a full reserve activation and leaves room for one:
        RD + RN times activation_hours <= SoC <= E - (RD + RN) times activation_hours

Prices are assumed known for the day (perfect foresight). The result is therefore
an upper bound on what a real forecast-based strategy could earn.
"""

from dataclasses import dataclass

import numpy as np

from .asset import BatteryAsset


@dataclass(frozen=True)
class DayPrices:
    da: np.ndarray      # EUR/MWh, day-ahead, one value per hour
    fcr_d: np.ndarray   # EUR/MW/h, FCR-D capacity
    fcr_n: np.ndarray   # EUR/MW/h, FCR-N capacity

    def __post_init__(self):
        n = len(self.da)
        if len(self.fcr_d) != n or len(self.fcr_n) != n:
            raise ValueError("price arrays must have the same length")


@dataclass
class DayDispatch:
    soc: np.ndarray         # MWh, length T + 1
    p_da: np.ndarray        # MW, +discharge / -charge, length T
    r_fcr_d: np.ndarray     # MW reserved, length T
    r_fcr_n: np.ndarray     # MW reserved, length T
    revenue_da: float       # EUR
    revenue_fcr_d: float    # EUR
    revenue_fcr_n: float    # EUR
    cycle_cost: float       # EUR
    value: float            # optimiser objective (equals net revenue on the grid)

    @property
    def revenue(self) -> float:
        return self.revenue_da + self.revenue_fcr_d + self.revenue_fcr_n - self.cycle_cost

    @property
    def throughput_mwh(self) -> float:
        return float(np.abs(self.p_da).sum())


def _action_table(power_mw: float, power_step: float):
    m = int(round(power_mw / power_step))
    levels = np.arange(-m, m + 1) * power_step
    res_levels = np.arange(0, m + 1) * power_step
    p, rd, rn = np.meshgrid(levels, res_levels, res_levels, indexing="ij")
    p, rd, rn = p.ravel(), rd.ravel(), rn.ravel()
    keep = (rd + rn + np.abs(p)) <= power_mw + 1e-9
    return p[keep], rd[keep], rn[keep]


def optimise_day(
    asset: BatteryAsset,
    prices: DayPrices,
    soc_start_mwh: float,
    power_step: float = 1.0,
    soc_step: float = 0.5,
) -> DayDispatch:
    """Return the revenue-maximising schedule for one day.

    power_step must divide the rated power. soc_step sets the SoC grid resolution;
    SoC is rounded to the nearest grid point after each hour, so with efficiency
    below 1 the schedule is an approximation of size soc_step / 2 per hour.
    """
    m = asset.power_mw / power_step
    if abs(m - round(m)) > 1e-9:
        raise ValueError("power_step must divide the rated power")

    T = len(prices.da)
    E = asset.energy_mwh
    n = int(round(E / soc_step)) + 1
    grid = np.linspace(0.0, E, n)
    step = grid[1] - grid[0]

    P, RD, RN = _action_table(asset.power_mw, power_step)
    R = RD + RN
    delta = np.maximum(-P, 0.0) * asset.eta_charge - np.maximum(P, 0.0) / asset.eta_discharge
    lo = R * asset.activation_hours
    hi = E - lo

    soc_next = grid[:, None] + delta[None, :]                       # (S, A)
    ok = (soc_next >= lo[None, :] - 1e-9) & (soc_next <= hi[None, :] + 1e-9)
    idx_next = np.rint(np.clip(soc_next, 0.0, E) / step).astype(int)

    V = np.zeros((T + 1, n))          # terminal value of stored energy is zero
    policy = np.zeros((T, n), dtype=int)
    for t in range(T - 1, -1, -1):
        reward = (
            P * prices.da[t]
            + RD * prices.fcr_d[t]
            + RN * prices.fcr_n[t]
            - asset.cycle_cost_eur_mwh * np.abs(P)
        )
        total = np.where(ok, reward[None, :] + V[t + 1][idx_next], -np.inf)
        policy[t] = total.argmax(axis=1)
        V[t] = total[np.arange(n), policy[t]]

    s = int(np.rint(soc_start_mwh / step))
    if not np.isfinite(V[0][s]):
        raise ValueError("starting SoC admits no feasible schedule")
    value = float(V[0][s])

    soc = np.empty(T + 1)
    soc[0] = grid[s]
    p = np.empty(T)
    rd = np.empty(T)
    rn = np.empty(T)
    for t in range(T):
        a = policy[t, s]
        p[t], rd[t], rn[t] = P[a], RD[a], RN[a]
        s = idx_next[s, a]
        soc[t + 1] = grid[s]

    return DayDispatch(
        soc=soc,
        p_da=p,
        r_fcr_d=rd,
        r_fcr_n=rn,
        revenue_da=float(np.sum(p * prices.da)),
        revenue_fcr_d=float(np.sum(rd * prices.fcr_d)),
        revenue_fcr_n=float(np.sum(rn * prices.fcr_n)),
        cycle_cost=float(asset.cycle_cost_eur_mwh * np.sum(np.abs(p))),
        value=value,
    )
