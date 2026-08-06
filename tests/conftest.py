"""Keep the test suite out of `data/` and off the operator's own credentials.

Two modules gained a default path that writes: `lib.reaping.JOURNAL` records every run,
and `connectors.oddsapi.USAGE` records the last quota reading so the spending floor
survives the process. Both are correct defaults for the program and wrong for a test run —
a full `pytest` wrote a 40KB journal and a usage file straight into `data/` beside the real
breaker state and the real outcome ledger.

Gitignore is not the guard here. The risk is not that the files get committed; it is that a
test run writes to the directory holding the money, and the failure that eventually
produces is a test that passes because it read something a previous test left behind — or
one that stamps a quota reading over the real one and stops a live lane at its floor.

So every test gets its own `data/` and has to opt back in explicitly. `monkeypatch` is
function-scoped, so this unwinds itself after each test.

The same argument covers the default **price source**. `status.as_json()` builds one when
no source is injected, and on a machine with `~/.alpaca/` present that is a live broker
call from a unit test — slow, rate-limited, and dependent on whose machine it runs on, so
the same test would pass here and fail in CI for a reason nothing states. The credentials
directory is pointed at an empty path instead, which makes the source report
COULD_NOT_LOOK and names why. Tests that need prices inject a fake and never touch this.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _keep_tests_out_of_the_live_data_directory(tmp_path, monkeypatch):
    """Redirect the write-by-default paths at their source modules.

    Patched on the module rather than passed per call, because the point is to catch the
    test nobody remembered to isolate — including tests written after this fixture.
    """

    import connectors.oddsapi
    import lib.pricing
    import lib.reaping

    monkeypatch.setattr(lib.reaping, "JOURNAL", tmp_path / "journal.sqlite3")
    monkeypatch.setattr(connectors.oddsapi, "USAGE", tmp_path / "oddsapi-usage.json")

    unconfigured = tmp_path / "no-alpaca-credentials"
    real_source = lib.pricing.alpaca_prices
    monkeypatch.setattr(
        lib.pricing, "alpaca_prices", lambda directory=None: real_source(unconfigured)
    )
    yield
