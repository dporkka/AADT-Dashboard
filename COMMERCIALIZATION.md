# AADT Dashboard Commercialization Review

## Decision

Treat this fork as **reference/research only**, not as the source repository for a commercial API.

There are two independent rights blockers:

1. This repository is a fork of `aditrademark/AADT-Dashboard`. GitHub reports no repository license on the upstream parent. Public visibility alone does not grant commercial reuse rights to upstream source code.
2. The checked-in 2021–2023 traffic workbooks match Arizona Department of Transportation (ADOT) AADT publication schemas. ADOT's website disclaimer states that reproduction permission may be required and that the State retains distribution rights to website information.

Do not sell, redistribute, or package the upstream dashboard code or checked-in ADOT datasets as marketplace inventory without explicit rights.

## Commercial product moved out of this fork

A separate **Traffic Forecast & Corridor Scenario API** implementation has been created under the private `api-factory/products/traffic-forecast-api` workspace.

That commercial package:

- does not import or vendor code from this upstream fork;
- does not bundle ADOT or any other transportation-agency dataset;
- accepts only caller-supplied traffic values;
- implements generic scenario mathematics in separately written code;
- labels all results as calculated scenarios, not official DOT/agency forecasts;
- requires a new commercial-rights review before any third-party dataset is added.

The commercial runtime, Docker packaging, marketplace OpenAPI, pricing metadata and tests should be maintained in that standalone product package rather than this fork.

## Source-data finding

The workbook schema matches ADOT annual Average Annual Daily Traffic publications, including fields such as `Loc ID`, route/road, BMP/EMP, K/D/T factors, current AADT and future AADT. ADOT now publishes newer vintages than the checked-in 2021–2023 files, so these files are also stale for a current raw-data product.

## Future raw traffic-data product

A normalized traffic-data API can be reconsidered only after one of these conditions is met:

1. an agency grants clear commercial redistribution/API rights;
2. a national/commercial dataset is licensed with redistribution rights; or
3. an original traffic-count acquisition pipeline is developed with rights owned by the business.

Until then, this fork should not be used as commercial code or data inventory.
