# Traffic Forecast & Corridor Scenario API

This marketplace product commercializes the dashboard's forecasting workflow without redistributing the source ADOT traffic datasets stored in the repository.

## Product boundary

The API accepts only **caller-supplied** traffic data and returns derived calculations. It does not load the repository's `AADT data/` or `AADT filtered data/` directories, and `Dockerfile.api` copies only `api/main.py` and `api/forecast.py` into the runtime image.

Returned projections are calculated scenarios, **not official ADOT/DOT forecasts**.

## Endpoints

- `POST /v1/forecast` — one scenario, up to 50 target years.
- `POST /v1/batch` — up to 200 independent scenarios.
- `POST /v1/corridor` — up to 500 segments at one target year, with range/mean summaries.
- `GET /v1/health` — RapidAPI-authenticated health.
- `GET /healthz` — container-platform liveness only.

## Calculation model

The API derives the compound annual growth rate implied by:

- current year / current AADT;
- reference year / reference AADT.

It then applies that rate to requested target years. When K/D/T factors are supplied, it also derives:

- design-hour volume = projected AADT × K;
- directional design-hour volume = design-hour volume × D;
- truck AADT = projected AADT × T.

Corridor analysis does **not** sum adjacent segment AADT, because segment traffic volumes are not additive. It reports minimum, maximum, mean, and (when BMP/EMP are supplied) length-weighted mean projected AADT.

## Local validation

```bash
cd api
python -m pip install -r requirements-dev.txt
RAPIDAPI_PROXY_SECRET=test-secret pytest -q
```

Run locally:

```bash
cd api
RAPIDAPI_PROXY_SECRET=test-secret uvicorn main:app --reload
```

Example:

```bash
curl http://localhost:8000/v1/forecast \
  -H 'Content-Type: application/json' \
  -H 'X-RapidAPI-Proxy-Secret: test-secret' \
  -d '{
    "external_id": "site-123",
    "current_year": 2025,
    "current_aadt": 24000,
    "reference_year": 2045,
    "reference_aadt": 36000,
    "target_years": [2030, 2035, 2045],
    "k_factor_percent": 9,
    "d_factor_percent": 55,
    "t_factor_percent": 8
  }'
```

## Container

```bash
docker build -f Dockerfile.api -t traffic-forecast-api .
docker run --rm -p 8080:8080 \
  -e RAPIDAPI_PROXY_SECRET=test-secret \
  traffic-forecast-api
```

## Marketplace launch

1. Deploy the isolated `Dockerfile.api` image to a stable HTTPS origin.
2. Configure a strong provider-only `RAPIDAPI_PROXY_SECRET`.
3. Import `marketplace/openapi.yaml` into RapidAPI Studio.
4. Confirm direct marketplace endpoints reject requests without the provider proxy secret.
5. Publish real Documentation, Terms, Privacy, Support, and Status links.
6. Start pricing as an experiment; computation is low-cost, but marketplace willingness-to-pay is not yet proven.
7. Smoke-test forecast, batch, corridor, invalid input, gateway rejection, and origin-unconfigured behavior through RapidAPI Runtime.

## Experimental pricing

| Plan | Price | Requests/month |
|---|---:|---:|
| BASIC | $0 | 50 |
| PRO | $29 | 2,000 |
| ULTRA | $99 | 10,000 |
| MEGA | $249 | 50,000 |

These are demand-testing prices, not a profitability claim. Batch and corridor calls can contain many calculations, so actual use patterns should be measured before quotas are finalized.

## Commercial rights

See `../COMMERCIALIZATION.md`. The raw ADOT workbooks remain outside the commercial API until explicit redistribution rights are documented. Customers are responsible for having rights/authorization to use the traffic data they submit.
