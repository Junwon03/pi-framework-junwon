# LTCM Historical Holdout Protocol Addendum v1.2

Status: PRE-OUTPUT IMPLEMENTATION CORRECTION

Parent documents:
- channel_selection_protocol_v1.md
- ltcm_protocol_addendum_v1_1.md

Protocol v1 freeze commit:
- a179608

Protocol v1.1 addendum commit:
- 3448f2e

## Reason for this correction

The first attempted FRED request failed before any observation data or
LTCM framework output was returned.

The frozen v1.1 specification set:

FRED_VINTAGE_DATE = 2026-09-10

At execution, the FRED API returned HTTP 400 and reported that its
current date was 2026-09-09 and that realtime_start could not be later
than that date.

Therefore the specified vintage was not executable at the time of the
first attempted holdout run.

No DFF, TEDRATE, or TOTBKCR observations were successfully retrieved,
and no LTCM stress, normalization, ratio, formulation, ablation,
correlation, permutation, or other framework result was generated or
inspected before this correction.

## Corrected FRED vintage

Replace:

FRED_VINTAGE_DATE = 2026-09-10

with:

FRED_VINTAGE_DATE = 2026-09-09

This is the latest calendar date accepted by FRED at the first attempted
execution and is fixed before any LTCM observation or framework result
has been obtained.

## No other changes

All event, channel, transformation, data-range, calibration, control,
post-control, normalization, alignment, interpolation, formulation,
ablation, permutation, block-size, seed, failure, and interpretation
rules remain unchanged.

The raw-data fetch range remains:

- LTCM_DATA_START = 1994-01-08
- LTCM_DATA_END = 1999-07-08
