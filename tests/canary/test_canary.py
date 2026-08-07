"""Deliberately-failing test that exercises the AI failure-analysis pipeline.

Marked only `canary` (not `api`/`ui`), so it's never selected by `-m api` or
`-m ui` and never runs on push/PR. Only runs via the "Run canary" checkbox on
a manual workflow_dispatch run in the Actions tab.
"""

import pytest

pytestmark = pytest.mark.canary


def calculate_total_price(price_per_night: int, nights: int) -> int:
    return price_per_night * nights + 1  # deliberate off-by-one bug


def test_canary_pipeline_smoke_test() -> None:
    assert calculate_total_price(price_per_night=100, nights=3) == 300
