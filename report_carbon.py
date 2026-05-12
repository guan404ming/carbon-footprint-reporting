"""Minimal illustrative decorator for the reporting format proposed in the paper.

This is intentionally a stub: it does not measure energy. It only formats and
emits the five fields the paper recommends, so authors can wire it onto a
training function and produce a uniform footer in the output log. A real
measurement backend (CodeCarbon, Carbontracker, nvidia-smi) would replace the
hardcoded numbers.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass


@dataclass
class CarbonReport:
    energy_kwh: float
    grid_intensity_gco2_per_kwh: float
    location: str
    pue: float | None = None

    @property
    def carbon_kgco2e(self) -> float:
        pue = self.pue or 1.0
        return self.energy_kwh * pue * self.grid_intensity_gco2_per_kwh / 1000

    def render(self, name: str) -> str:
        return (
            f"[Carbon Report] {name}\n"
            f"  Energy:          {self.energy_kwh:.2f} kWh\n"
            f"  Carbon:          {self.carbon_kgco2e:.2f} kgCO2e\n"
            f"  Grid intensity:  {self.grid_intensity_gco2_per_kwh:g} gCO2/kWh\n"
            f"  PUE:             {self.pue if self.pue is not None else 'n/a'}\n"
            f"  Location:        {self.location}"
        )


def report_carbon(
    energy_kwh: float,
    grid_intensity_gco2_per_kwh: float,
    location: str,
    pue: float | None = None,
):
    """Decorator that appends a standardized carbon report after the wrapped call."""

    report = CarbonReport(
        energy_kwh=energy_kwh,
        grid_intensity_gco2_per_kwh=grid_intensity_gco2_per_kwh,
        location=location,
        pue=pue,
    )

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            print(report.render(fn.__name__))
            return result

        wrapper.carbon_report = report
        return wrapper

    return decorator


if __name__ == "__main__":

    @report_carbon(
        energy_kwh=85.2,
        grid_intensity_gco2_per_kwh=350,
        pue=1.2,
        location="Frankfurt, DE",
    )
    def train():
        return "model"

    train()
