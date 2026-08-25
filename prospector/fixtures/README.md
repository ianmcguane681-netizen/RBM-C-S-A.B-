# Fixtures

`synthetic-area.overpass.json` is **invented**, not a saved query. No real business appears
in it, and the names are made up. It exists so `python -m prospector --from-file` exercises
every branch of the cascade on a machine that cannot reach a live Overpass endpoint, which
includes any sandbox that blocks it.

The websites in it are deliberately a mix: one address that does not resolve, one social
page, one site that is genuinely fine, and several businesses with no website listed at
all. Running against it should PREPARE some, REFUSE others by name, and leave at least one
INDETERMINATE — because a fixture where everything succeeds tests nothing worth testing.
