# AADT Dashboard Commercialization Review

## Decision

Do **not** sell or redistribute the checked-in Arizona Department of Transportation (ADOT) AADT spreadsheets as marketplace API inventory without explicit permission or a separate license that clearly permits commercial redistribution.

Commercialize the repository's **calculation/workflow layer** instead: customers supply traffic counts and any reference forecast values they are authorized to use, and the API returns derived scenario projections and planning signals.

## Source identification

The checked-in 2021–2023 workbook schema matches ADOT's published Average Annual Daily Traffic reports, including fields such as:

- `Loc ID`
- `Road` / `Route`
- `BMP` / `EMP`
- `FromRoad` / `ToRoad`
- `AADT <year>`
- `K Factor %`
- `D Factor %`
- `T Factor %`
- `<future year> Future AADT`

ADOT's Traffic Monitoring site publishes annual AADT reports in PDF/Excel form and currently exposes newer 2024/2025 vintages as well. That means the repository's 2021–2023 files are also stale for a raw-data marketplace product.

## Rights gate

ADOT's website disclaimer states that documents may be protected by copyright, permission to reproduce may be required, and the State of Arizona retains rights to information provided by the website, including distribution rights.

Until written permission or other clear commercial-redistribution rights are documented, treat the source spreadsheets as **reference/internal inputs only**, not resale inventory.

## Product to sell instead

**Traffic Forecast & Site Analysis API**

Caller supplies:

- current AADT and current year
- a future/reference AADT and reference year
- requested projection years
- optional K, D, and T factors
- optional route / BMP / EMP segment metadata

API returns:

- implied compound annual growth rate
- projected AADT by requested year
- optional design-hour volume from K factor
- optional directional design-hour volume from K × D
- optional truck AADT from T factor
- batch calculations
- corridor segment projections and non-additive range/mean summaries

## Claim boundary

Every marketplace response and listing must make clear that:

- inputs are supplied by the customer;
- outputs are BusinessFinder-derived calculations;
- projections are **not official ADOT/DOT forecasts**;
- the commercial API does not bundle, query, copy, or redistribute the checked-in ADOT workbooks;
- adjacent segment AADT is not summed into a fictitious corridor traffic total.

## Future expansion

A raw/normalized traffic-data API can be reconsidered only after one of the following is true:

1. ADOT or another source grants clear commercial redistribution rights;
2. the business licenses a national traffic dataset with redistribution/API rights; or
3. an original traffic-count acquisition pipeline is developed with rights owned by the business.

Until then, the algorithm-only product is the safer marketplace opportunity.
