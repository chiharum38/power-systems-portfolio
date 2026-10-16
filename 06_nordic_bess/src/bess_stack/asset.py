from dataclasses import dataclass


@dataclass(frozen=True)
class BatteryAsset:
    """A grid-scale battery. Power in MW, energy in MWh, prices in EUR."""

    power_mw: float
    energy_mwh: float
    eta_charge: float = 0.92
    eta_discharge: float = 0.92
    soc0_frac: float = 0.5
    # Energy needed to fully activate one MW of reserve, in hours.
    # Assumption: a reserve activation lasts 15 minutes, so SoC must cover it.
    activation_hours: float = 0.25
    cycle_cost_eur_mwh: float = 0.0

    def __post_init__(self):
        if self.power_mw <= 0 or self.energy_mwh <= 0:
            raise ValueError("power and energy must be positive")
        if not 0.0 < self.eta_charge <= 1.0 or not 0.0 < self.eta_discharge <= 1.0:
            raise ValueError("efficiencies must be in (0, 1]")
        if not 0.0 <= self.soc0_frac <= 1.0:
            raise ValueError("soc0_frac must be in [0, 1]")
        if self.activation_hours < 0:
            raise ValueError("activation_hours must be non-negative")

    @property
    def duration_h(self) -> float:
        return self.energy_mwh / self.power_mw
