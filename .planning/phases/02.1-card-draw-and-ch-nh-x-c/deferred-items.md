# Deferred Items - Phase 02.1

## Out-of-scope flaky test (discovered during plan 02)

**test_fsm.py::TestPrisonHandling::test_prison_player_skips_roll**

- **Issue:** Test is non-deterministic. Player in prison with cash=0 goes to "lựa chọn B" (roll dice). If doubles are rolled, player exits prison and goes to MOVE phase (not END_TURN). The test expects END_TURN but fails ~16% of the time (1 in 6 chance per die pair).
- **Root cause:** Pre-existing issue in test design — test doesn't mock `roll_dice` to return non-doubles.
- **Fix needed:** Mock `self.roll_dice` to return non-doubles in `test_prison_player_skips_roll`.
- **Scope:** Not caused by plan 02 changes. Out of scope for current plan.
