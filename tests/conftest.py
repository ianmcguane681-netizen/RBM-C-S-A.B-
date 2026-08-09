"""Keep the test suite out of `data/`, which is the live operational directory.

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
    import lib.announce
    import lib.journal
    import lib.notify
    import lib.reaping

    monkeypatch.setattr(lib.reaping, "JOURNAL", tmp_path / "journal.sqlite3")
    # Two constants, because two modules resolve it: `lib.reaping` writes the diary and
    # the daily digest READS it to say what each lane found. Patching only the writer
    # leaves a test summarising the live journal into a message.
    monkeypatch.setattr(lib.journal, "JOURNAL", tmp_path / "journal.sqlite3")
    monkeypatch.setattr(connectors.oddsapi, "USAGE", tmp_path / "oddsapi-usage.json")
    monkeypatch.setattr(lib.notify, "LOG", tmp_path / "notifications.json")
    monkeypatch.setattr(lib.announce, "MEMORY", tmp_path / "announced.json")
    yield


@pytest.fixture(autouse=True)
def _no_test_ever_messages_a_person(monkeypatch):
    """`default_announcer()` reads `~/.telegram`, and on a configured machine it sends.

    Every path that announces resolves its channel through that one function, so patching
    it here means a test that reaches the notifier by accident — through `reap()`, through
    the supervisor, through a fourth lane written later — gets a silent announcer that
    reports NOT_CONFIGURED instead of buzzing somebody's phone at three in the morning.

    Redirecting the credentials directory would not do: the failure worth preventing is a
    test run on the machine where the credentials are real, which is exactly the machine
    the suite is run on before anything is deployed.
    """

    import lib.announce
    import lib.reaping

    monkeypatch.setattr(lib.announce, "default_announcer",
                        lambda **kw: lib.announce.Announcer(None, **kw))
    monkeypatch.setattr(lib.reaping, "default_announcer",
                        lambda: lib.announce.Announcer(None))
    yield
