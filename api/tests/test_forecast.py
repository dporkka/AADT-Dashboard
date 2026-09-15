from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from forecast import ForecastInputs, compound_annual_growth_rate, project_aadt
from main import app


PROXY_SECRET = "test-marketplace-secret"
HEADERS = {"X-RapidAPI-Proxy-Secret": PROXY_SECRET}


def setup_module() -> None:
    os.environ["RAPIDAPI_PROXY_SECRET"] = PROXY_SECRET


def test_compound_growth_and_projection() -> None:
    inputs = ForecastInputs(
        current_year=2020,
        current_aadt=10_000,
        reference_year=2022,
        reference_aadt=12_100,
    )
    assert round(compound_annual_growth_rate(inputs), 8) == 0.1
    assert project_aadt(inputs, 2021).projected_aadt == 11_000
    assert project_aadt(inputs, 2024).projected_aadt == 14_641


def test_kdt_outputs() -> None:
    inputs = ForecastInputs(
        current_year=2020,
        current_aadt=10_000,
        reference_year=2022,
        reference_aadt=12_100,
        k_factor_percent=10,
        d_factor_percent=60,
        t_factor_percent=5,
    )
    result = project_aadt(inputs, 2021)
    assert result.design_hour_volume == 1_100
    assert result.directional_design_hour_volume == 660
    assert result.truck_aadt == 550


def test_marketplace_origin_fails_closed() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/forecast",
            json={
                "current_year": 2024,
                "current_aadt": 20_000,
                "reference_year": 2044,
                "reference_aadt": 30_000,
                "target_years": [2030],
            },
        )
    assert response.status_code == 403


def test_forecast_endpoint_returns_derived_scenario() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/forecast",
            headers=HEADERS,
            json={
                "external_id": "site-123",
                "current_year": 2020,
                "current_aadt": 10_000,
                "reference_year": 2022,
                "reference_aadt": 12_100,
                "target_years": [2021, 2024],
                "k_factor_percent": 10,
                "d_factor_percent": 60,
                "t_factor_percent": 5,
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["external_id"] == "site-123"
    assert payload["result"]["annual_growth_rate_percent"] == 10
    assert payload["result"]["forecasts"][0]["projected_aadt_rounded"] == 11_000
    assert "official" not in payload["result"]["methodology"].lower()


def test_batch_endpoint_preserves_scenario_ids() -> None:
    scenario = {
        "current_year": 2024,
        "current_aadt": 15_000,
        "reference_year": 2044,
        "reference_aadt": 22_000,
        "target_years": [2030],
    }
    with TestClient(app) as client:
        response = client.post(
            "/v1/batch",
            headers=HEADERS,
            json={
                "scenarios": [
                    {**scenario, "external_id": "a"},
                    {**scenario, "external_id": "b"},
                ]
            },
        )
    assert response.status_code == 200
    assert [item["external_id"] for item in response.json()["results"]] == ["a", "b"]


def test_corridor_does_not_sum_adjacent_segment_aadt() -> None:
    segment = {
        "current_year": 2024,
        "current_aadt": 20_000,
        "reference_year": 2044,
        "reference_aadt": 30_000,
        "route": "SR-1",
    }
    with TestClient(app) as client:
        response = client.post(
            "/v1/corridor",
            headers=HEADERS,
            json={
                "target_year": 2030,
                "segments": [
                    {**segment, "segment_id": "s1", "bmp": 0, "emp": 1},
                    {
                        **segment,
                        "segment_id": "s2",
                        "current_aadt": 25_000,
                        "reference_aadt": 35_000,
                        "bmp": 1,
                        "emp": 3,
                    },
                ],
            },
        )
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert "total_projected_aadt" not in summary
    assert summary["minimum_projected_aadt"] < summary["maximum_projected_aadt"]
    assert summary["length_weighted_mean_projected_aadt"] is not None


def test_invalid_reference_year_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/forecast",
            headers=HEADERS,
            json={
                "current_year": 2024,
                "current_aadt": 20_000,
                "reference_year": 2024,
                "reference_aadt": 30_000,
                "target_years": [2030],
            },
        )
    assert response.status_code == 422
