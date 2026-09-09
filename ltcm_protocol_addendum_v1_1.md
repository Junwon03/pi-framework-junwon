# LTCM Historical Holdout Protocol Addendum v1.1

Status: PRE-OUTPUT AMENDMENT

Parent protocol:
- channel_selection_protocol_v1.md
- freeze commit: a179608
- SHA-256: 1a843d8cae550da2019c2bb8f39c38a5c7be11c5d8d75aa432cd5a3d33701f8d

## Reason for this addendum

A source-code audit conducted after protocol v1 was frozen but before
any LTCM framework output was generated identified two implementation
parameters that require explicit specification for deterministic
reproduction:

1. the FRED vintage date;
2. the raw-data fetch boundaries.

No LTCM stress, ratio, formulation, ablation, correlation, permutation,
or other framework outcome had been computed or inspected before this
amendment.

## Frozen FRED vintage

FRED_VINTAGE_DATE = 2026-09-10

All three FRED series (DFF, TEDRATE, TOTBKCR) shall be requested using
this same realtime_start and realtime_end vintage date.

The FRED API key is an authentication secret and is not part of the
scientific specification.

## Frozen raw-data fetch range

The 2008 development configuration used:

- DATA_START = 2004-01-01
- DATA_END = 2009-06-30
- reference date = 2008-09-15

These correspond to reference-date offsets of:

- DATA_START: -1719 calendar days
- DATA_END: +288 calendar days

Applying those offsets mechanically to the frozen LTCM reference date
1998-09-23 gives:

- LTCM_DATA_START = 1994-01-08
- LTCM_DATA_END = 1999-07-08

These are raw-data retrieval boundaries only.

The previously frozen evaluation boundaries remain unchanged:

- control: 1994-01-08 through 1996-07-07
- calibration: 1995-01-09 through 1997-07-07
- post-control: first valid observation strictly after 1996-07-07
  through 1999-04-08

Observations outside the evaluation boundaries may support the
prespecified five-observation transformation or lower-frequency
interpolation but shall not enter control, calibration, or post-control
statistics unless their transformed timestamps fall within the frozen
evaluation windows.

## No other changes

All episode, channel, transformation, normalization, alignment,
interpolation, evaluation, formulation, ablation, permutation,
block-size, seed, failure, and interpretation rules in protocol v1
remain unchanged.
