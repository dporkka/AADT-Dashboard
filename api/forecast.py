"""Pure traffic-forecast calculations extracted from the dashboard concept.

This module contains no source traffic dataset and performs no data acquisition.
All traffic counts, factors, route identifiers, and reference forecasts are supplied
by the caller. Returned projections are BusinessFinder-derived calculations, not
official forecasts from a transportation agency.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Iterable


@dataclass(frozen=True)
class ForecastInputs:
    current_year: int
    current_aadt: float
    reference_year: int
    reference_aadt: float
    k_factor_percent: float | None = None
    d_factor_percent: float | None = None
    t_factor_percent: float | None = None


@dataclass(frozen=True)
class ForecastValues:
    target_year: int
    projected_aadt: float
    projected_aadt_rounded: int
    design_hour_volume: float | None
    directional_design_hour_volume: float | None
    truck_aadt: float | None


def compound_annual_growth_rate(inputs: ForecastInputs) -> float:
    """Return the annual growth rate implied by current/reference AADT values."""

    if inputs.current_aadt <= 0 or inputs.reference_aadt <= 0:
        raise ValueError("AADT values must be greater than zero")
    if inputs.reference_year <= inputs.current_year:
        raise ValueError("reference_year must be greater than current_year")

    years = inputs.reference_year - inputs.current_year
    return (inputs.reference_aadt / inputs.current_aadt) ** (1.0 / years) - 1.0


def project_aadt(inputs: ForecastInputs, target_year: int) -> ForecastValues:
    """Project AADT and optional K/D/T planning values for one target year."""

    if target_year < inputs.current_year:
        raise ValueError("target_year cannot be earlier than current_year")

    growth_rate = compound_annual_growth_rate(inputs)
    projected = inputs.current_aadt * (1.0 + growth_rate) ** (
        target_year - inputs.current_year
    )

    design_hour = (
        projected * inputs.k_factor_percent / 100.0
        if inputs.k_factor_percent is not None
        else None
    )
    directional_design_hour = (
        design_hour * inputs.d_factor_percent / 100.0
        if design_hour is not None and inputs.d_factor_percent is not None
        else None
    )
    truck_aadt = (
        projected * inputs.t_factor_percent / 100.0
        if inputs.t_factor_percent is not None
        else None
    )

    return ForecastValues(
        target_year=target_year,
        projected_aadt=round(projected, 4),
        projected_aadt_rounded=round(projected),
        design_hour_volume=round(design_hour, 4) if design_hour is not None else None,
        directional_design_hour_volume=(
            round(directional_design_hour, 4)
            if directional_design_hour is not None
            else None
        ),
        truck_aadt=round(truck_aadt, 4) if truck_aadt is not None else None,
    )


def summarize_projected_aadt(
    values: Iterable[tuple[float, float | None]],
) -> dict[str, float | None]:
    """Summarize segment AADT without pretending segment volumes are additive.

    ``values`` contains ``(projected_aadt, segment_length)`` tuples. AADT on adjacent
    segments should generally not be summed, so this returns range/means instead.
    """

    rows = list(values)
    if not rows:
        return {
            "minimum_projected_aadt": None,
            "maximum_projected_aadt": None,
            "mean_projected_aadt": None,
            "length_weighted_mean_projected_aadt": None,
        }

    aadts = [item[0] for item in rows]
    weighted_rows = [item for item in rows if item[1] is not None and item[1] > 0]
    total_length = sum(item[1] for item in weighted_rows if item[1] is not None)
    weighted_mean = None
    if total_length > 0:
        weighted_mean = sum(
            aadt * float(length) for aadt, length in weighted_rows if length is not None
        ) / total_length

    return {
        "minimum_projected_aadt": round(min(aadts), 4),
        "maximum_projected_aadt": round(max(aadts), 4),
        "mean_projected_aadt": round(fmean(aadts), 4),
        "length_weighted_mean_projected_aadt": (
            round(weighted_mean, 4) if weighted_mean is not None else None
        ),
    }
