# Revision Analysis Decision Record

Date: 2026-07-31
Status: Post-review revision decision record; this is not a preregistration.

## Purpose

This record fixes the remaining revision analyses before implementation.
The choices below are motivated by crisis-control overlap, unequal window
duration, temporal autocorrelation, and reproducibility concerns. They will
not be altered in response to whether the resulting estimates are favorable.

## 1. Primary comparison

The revised primary estimand is:

mean stress in crisis observations strictly after the prespecified control
window end divided by mean stress in the full prespecified control window.

The original full-window cumulative ratio and full-window mean ratio will be
retained as legacy descriptive quantities rather than deleted or replaced.

## 2. Crisis-exclusive permutation diagnostic

The permutation analysis will be restricted to the same crisis-exclusive
segment used by the primary comparison.

It tests whether the observed temporal alignment of rho, psi, and omega within
that segment exceeds alignment obtained after independently disrupting the
channel sequences. It is not a direct hypothesis test of the crisis-control
mean difference.

Fixed settings:

- 10,000 permutations
- deterministic local random-number generation with documented fixed seeds
- independent channel shuffling for the independent diagnostic
- block sizes 5, 10, and 20 for daily cases
- block sizes 2, 3, and 4 for the monthly Supply Chain case
- all five selected cases reported
- no block size, seed, case, or reporting threshold changed after inspection
  of results
- zero exceedances reported using the finite Monte Carlo resolution rather
  than as p = 0

The original full-crisis-window permutation tables remain archived as legacy
diagnostics.

## 3. Additional comparison cases

No further cases will be added during this revision.

For Dot-com, 2019 Repo, and Thailand Floods, both metrics will be preserved:

- legacy cumulative ratio
- primary mean-stress ratio

The mean-stress ratio will be used for comparison with the revised primary
estimand. Cases will not be classified as positive or negative by selecting
whichever metric gives the preferred direction.

These cases are exploratory comparison or boundary cases, not formal negative
controls and not independent validation episodes.

## 4. Formulation comparison

The statement that the multiplicative formulation ranks highest in five of
five selected cases applies only among the three three-channel formulations:

- rho x psi x omega
- rho + psi + omega
- max(rho, psi, omega)

It does not claim that the three-channel product outperforms every single- or
dual-channel ablation. The Supply Chain psi x omega result will remain visible
as a non-redundancy boundary condition.

## 5. Variable specification provenance

A specification provenance table will report:

- selected variable
- transformation
- source
- domain rationale
- calibration period
- whether selection involved iterative or post hoc judgment
- only alternatives that were actually tested
- frozen input artifact

The table will not be described as a preregistered protocol.

## 6. Reproducibility controls

- canonical input path: data/
- primary and additional-case frozen CSV inputs checked against golden/data/
- generated deterministic outputs checked against golden/output/
- both verifier entry points must return success
- retired ST16 outputs remain excluded from active evidence
- golden baselines will be updated only after inspecting and explaining every
  deterministic difference
- the complete pipeline must pass locally and in Linux CI before consolidation

## 7. Scope limit

This revision is a retrospective characterization of selected cases. It does
not establish universal validation, prospective prediction, calibrated
false-alarm performance, or population-level cross-domain generalization.
A properly powered many-episode or prospective design remains future work.
