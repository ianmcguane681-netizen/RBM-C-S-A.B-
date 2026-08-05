web: python -m backend
# The lanes have cadences and nothing was invoking them: this file declared a web process
# and no worker, and there was no cron entry or timer anywhere. `--go` runs what is due and
# exits, so without this line the cadences describe an intention rather than a schedule.
worker: python run.py --serve
