"""Marketplace-ready traffic forecasting API.

The service accepts caller-supplied traffic counts/reference forecasts and returns
BusinessFinder-derived calculations. It does not bundle, query, or redistribute the
ADOT spreadsheets stored elsewhere in this repository.
"""

from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, FastAPI, Header, HTTPException, Response, status
from pydantic import BaseModel, Field, model_validator

from forecast import ForecastInputs, compound_annual_growth_rate, project_aadt, summarize_projected_aadt


app = FastAPI(
    title="Traffic Forecast & Site Analysis API",
    version="1.0.0",
    description=(
        "Project caller-supplied AADT values and derive optional K/D/T planning "
        "signals. Returned projections are calculated scenarios, not official DOT forecasts."
    ),
)
router = APIRouter(prefix="/v1")


class ScenarioInput(BaseModel):
    external_id: str | None = Field(default=None, max_length=128)
    current_year: int = Field(ge=1900, le=2200)
    current_aadt: float = Field(gt=0, le=100_000_000)
    reference_year: int = Field(ge=1901, le=2300)
    reference_aadt: float = Field(gt=0, le=100_000_000)
    target_years: list[int] = Field(min_length=1, max_length=50)
    k_factor_percent: float | None = Field(default=None, ge=0, le=100)
    d_factor_percent: float | None = Field(default=None, ge=0, le=100)
    t_factor_percent: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_years(self) -> "ScenarioInput":
        if self.reference_year <= self.current_year:
            raise ValueError("reference_year must be greater than current_year")
        if any(year < self.current_year for year in self.target_years):
            raise ValueError("target_years cannot contain years before current_year")
        if any(year > self.current_year + 100 for year in self.target_years):
            raise ValueError("target_years are limited to 100 years beyond current_year")
        return self


class ForecastPoint(BaseModel):
    target_year: int
    projected_aadt: float
    projected_aadt_rounded: int
    design_hour_volume: float | None = None
    directional_design_hour_volume: float | None = None
    truck_aadt: float | None = None


class ScenarioResult(BaseModel):
    external_id: str | None = None
    annual_growth_rate: float
    annual_growth_rate_percent: float
    forecasts: list[ForecastPoint]
    methodology: str


class ForecastResponse(BaseModel):
    success: bool = True
    result: ScenarioResult
    calculated_at: str


class BatchRequest(BaseModel):
    scenarios: list[ScenarioInput] = Field(min_length=1, max_length=200)


class BatchResponse(BaseModel):
    success: bool = True
    results: list[ScenarioResult]
    calculated_at: str


class CorridorSegment(ScenarioInput):
    segment_id: str = Field(min_length=1, max_length=128)
    route: str | None = Field(default=None, max_length=128)
    bmp: float | None = None
    emp: float | None = None

    @model_validator(mode="after")
    def validate_segment(self) -> "CorridorSegment":
        if self.bmp is not None and self.emp is not None and self.emp <= self.bmp:
            raise ValueError("emp must be greater than bmp when both are supplied")
        return self


class CorridorRequest(BaseModel):
    target_year: int = Field(ge=1900, le=2300)
    segments: list[CorridorSegment] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_target(self) -> "CorridorRequest":
        for segment in self.segments:
            if self.target_year < segment.current_year:
                raise ValueError(
                    f"target_year cannot be earlier than current_year for {segment.segment_id}"
                )
        return self


class CorridorSegmentResult(BaseModel):
    segment_id: str
    route: str | None = None
    bmp: float | None = None
    emp: float | None = None
    segment_length: float | None = None
    annual_growth_rate_percent: float
    forecast: ForecastPoint


class CorridorResponse(BaseModel):
    success: bool = True
    target_year: int
    segments: list[CorridorSegmentResult]
    summary: dict[str, float | None]
    methodology: str
    calculated_at: str


def _expected_proxy_secret() -> str:
    value = os.getenv("RAPIDAPI_PROXY_SECRET", "")
    if not value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Marketplace origin is not configured",
        )
    return value


def verify_marketplace_gateway(
    x_rapidapi_proxy_secret: Annotated[str | None, Header()] = None,
) -> None:
    expected = _expected_proxy_secret()
    if not x_rapidapi_proxy_secret or not hmac.compare_digest(
        x_rapidapi_proxy_secret, expected
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request must arrive through the configured marketplace gateway",
        )


def _inputs(value: ScenarioInput) -> ForecastInputs:
    return ForecastInputs(
        current_year=value.current_year,
        current_aadt=value.current_aadt,
        reference_year=value.reference_year,
        reference_aadt=value.reference_aadt,
        k_factor_percent=value.k_factor_percent,
        d_factor_percent=value.d_factor_percent,
        t_factor_percent=value.t_factor_percent,
    )


def _result(value: ScenarioInput) -> ScenarioResult:
    inputs = _inputs(value)
    growth = compound_annual_growth_rate(inputs)
    points = [ForecastPoint(**project_aadt(inputs, year).__dict__) for year in value.target_years]
    return ScenarioResult(
        external_id=value.external_id,
        annual_growth_rate=round(growth, 8),
        annual_growth_rate_percent=round(growth * 100.0, 6),
        forecasts=points,
        methodology=(
            "Compound annual growth rate implied by the caller-supplied current and "
            "reference AADT values; the same growth rate is applied to requested years. "
            "K/D/T outputs, when supplied, are arithmetic derivatives of projected AADT."
        ),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/forecast", response_model=ForecastResponse)
def forecast(
    payload: ScenarioInput,
    _: None = Annotated[None, verify_marketplace_gateway],
) -> ForecastResponse:
    return ForecastResponse(result=_result(payload), calculated_at=_now())


@router.post("/batch", response_model=BatchResponse)
def batch_forecast(
    payload: BatchRequest,
    _: None = Annotated[None, verify_marketplace_gateway],
) -> BatchResponse:
    return BatchResponse(
        results=[_result(item) for item in payload.scenarios],
        calculated_at=_now(),
    )


@router.post("/corridor", response_model=CorridorResponse)
def corridor_analysis(
    payload: CorridorRequest,
    _: None = Annotated[None, verify_marketplace_gateway],
) -> CorridorResponse:
    rows: list[CorridorSegmentResult] = []
    summary_values: list[tuple[float, float | None]] = []

    for segment in payload.segments:
        inputs = _inputs(segment)
        growth = compound_annual_growth_rate(inputs)
        point = ForecastPoint(**project_aadt(inputs, payload.target_year).__dict__)
        segment_length = (
            round(segment.emp - segment.bmp, 6)
            if segment.bmp is not None and segment.emp is not None
            else None
        )
        rows.append(
            CorridorSegmentResult(
                segment_id=segment.segment_id,
                route=segment.route,
                bmp=segment.bmp,
                emp=segment.emp,
                segment_length=segment_length,
                annual_growth_rate_percent=round(growth * 100.0, 6),
                forecast=point,
            )
        )
        summary_values.append((point.projected_aadt, segment_length))

    return CorridorResponse(
        target_year=payload.target_year,
        segments=rows,
        summary=summarize_projected_aadt(summary_values),
        methodology=(
            "Segment projections use caller-supplied current/reference AADT. Corridor "
            "summary reports ranges and means rather than summing adjacent segment AADT."
        ),
        calculated_at=_now(),
    )


@router.get("/health")
def marketplace_health(
    _: None = Annotated[None, verify_marketplace_gateway],
) -> dict[str, str]:
    return {"status": "healthy", "service": "traffic-forecast", "timestamp": _now()}


@app.get("/healthz", include_in_schema=False)
def platform_health() -> dict[str, str]:
    return {"status": "healthy", "service": "traffic-forecast"}


app.include_router(router)
