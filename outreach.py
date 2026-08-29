"""Find local businesses whose web presence is worth a conversation, and draft one.

    python outreach.py                          run the configured areas
    python outreach.py --leads                  just the businesses to go and search for
    python outreach.py --searched node/123 --url https://... --by "Your Name"
    python outreach.py --searched node/456 --none --by "Your Name"
    python outreach.py --suppress node/789 "asked not to be contacted"
    python outreach.py --sent node/123          record that you sent the draft

    exit 0  nothing to act on          1  drafts are waiting        2  nothing was looked at

**Nothing is sent.** There is no SMTP client in this repository and no key path for one,
the same way `connectors/chain_exec.py` has no signing library. The deliverable is a draft
with an address on it and a person presses send. Do not add one.

## The loop this is built around

The awkward part of this lane is that OpenStreetMap can tell you a business exists and
cannot tell you whether it has a website — its coverage of premises is far better than its
coverage of attributes, so an absent `website` tag is a LEAD rather than a finding. No free
search API exists to close that gap and a scraped search page would be both against the
terms and wrong often enough to matter.

So the loop has a person in it, once, for thirty seconds per business:

    run it        -> a list of leads with contact details and addresses
    --leads       -> the ones needing a search
    --searched    -> record what you found: a URL, or nothing
    run it again  -> the URLs get checked, the nothings become drafts

That is more work than a lead-generation tool that just asserts things, and it is the
difference between an approach that opens with something true about somebody's business and
one that opens by telling them they have no website when they do.

## What it will refuse to draft

An approach to an address that looks like a named individual's rather than a company's; to
anybody on the suppression list; to anybody written to inside the cooldown; and about any
site it did not actually reach. `lib/outreach.py` argues each of those where it is enforced.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib.outreach import (
    APPROACHES,
    NEEDS_WORK,
    NO_SITE_FOUND,
    NOT_ESTABLISHED,
    SEARCHES,
    SUPPRESSION,
    ApproachLog,
    SearchLog,
    SuppressionList,
    assess,
    draft,
    summarise,
)

CONFIG = Path("data/outreach.json")

TEMPLATE = {
    "_README": [
        "Copy to data/outreach.json. That path is gitignored: it records which towns and",
        "which businesses are being approached, and this repository is public.",
        "",
        "`sender` and `sender_detail` are mandatory. An unsolicited business message must",
        "identify who is sending it, and this refuses to draft one that cannot.",
        "",
        "Areas are small bounding boxes — south, west, north, east — of at most 0.25",
        "degrees. Overpass is donated infrastructure with no key; cover more ground with",
        "more small queries over time rather than one large one now."
    ],
    "sender": "YOUR NAME",
    "sender_detail": "I build small websites for local businesses in <your town>",
    "areas": [
        {"name": "Cork city centre", "south": 51.888, "west": -8.500,
         "north": 51.909, "east": -8.455}
    ],
    "categories": [
        "shop=hairdresser", "craft=plumber", "craft=electrician", "amenity=cafe"
    ],
    "check_sites": True,
}


def load_config(path: Path) -> tuple[dict, str]:
    if not path.is_file():
        return {}, ""
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except (OSError, ValueError) as error:
        return {}, f"{type(error).__name__}: {error}"


def gather(config: dict, *, searches: SearchLog, suppression: SuppressionList,
           log: ApproachLog, opener=None) -> tuple[list, list[str]]:
    """Every configured area, assessed. Returns `(prospects, coverage notes)`.

    A silent area is a note rather than an omission, for the reason every lane here keeps
    repeating: a run that reached two of five areas and reported six prospects has said
    nothing whatever about the other three towns.
    """

    from connectors.directory import READ, Area, businesses_in, describe_coverage
    from connectors.sitecheck import check

    from lib.http_retry import retrying_urlopen

    categories = tuple(config.get("categories") or ())
    listings, prospects = [], []

    for row in config.get("areas") or ():
        try:
            area = Area(south=float(row["south"]), west=float(row["west"]),
                        north=float(row["north"]), east=float(row["east"]),
                        name=str(row.get("name", "")))
        except (KeyError, TypeError, ValueError) as error:
            listings.append(type("Bad", (), {
                "status": "REFUSED", "area": str(row.get("name", "an area")),
                "businesses": (), "reason": str(error)})())
            continue

        listing = (businesses_in(area, categories=categories, opener=opener or
                                 retrying_urlopen)
                   if categories else businesses_in(area, opener=opener or
                                                    retrying_urlopen))
        listings.append(listing)
        if listing.status != READ:
            continue

        for business in listing.businesses:
            site = None
            if config.get("check_sites", True):
                # The recorded URL first, then whatever a person found in a search. Both
                # are addresses somebody put there; neither is guessed from a name.
                url = business.website
                if not url:
                    status, found, _ = searches.find(business.osm_id)
                    url = found if status == "FOUND" else ""
                if url:
                    site = check(url)
            prospects.append(assess(business, site, suppression=suppression, log=log,
                                    searches=searches))

    return prospects, [describe_coverage(listings)]


def run(config: dict, *, leads_only: bool = False) -> int:
    searches = SearchLog.load(SEARCHES)
    suppression = SuppressionList.load(SUPPRESSION)
    log = ApproachLog.load(APPROACHES)

    prospects, coverage = gather(config, searches=searches, suppression=suppression,
                                 log=log)
    for note in coverage:
        print(note)
    print("")

    if not prospects:
        print("No business was assessed. That is a statement about the areas that "
              "answered, and says nothing about a town that did not.")
        return 2

    print(summarise(prospects))
    print("")

    leads = [p for p in prospects if p.finding == NOT_ESTABLISHED]
    if leads_only or not any(p.finding in {NEEDS_WORK, NO_SITE_FOUND} for p in prospects):
        print(f"{len(leads)} lead(s) need somebody to look, thirty seconds each:")
        for prospect in leads:
            business = prospect.business
            print(f"  {business.name}  osm:{business.osm_id}"
                  + (f"  {business.address}" if business.address else ""))
            print(f"    python outreach.py --searched {business.osm_id} "
                  f"--url <URL> --by \"Your Name\"   (or --none)")
        return 1 if leads else 0

    sender = str(config.get("sender", ""))
    detail = str(config.get("sender_detail", ""))
    drafted = 0
    for prospect in prospects:
        if prospect.finding in {NOT_ESTABLISHED}:
            continue
        approach = draft(prospect, sender=sender, sender_detail=detail)
        if isinstance(approach, str):
            print(f"NOT DRAFTED  {prospect.name}: {approach}")
            print("")
            continue
        drafted += 1
        print(approach.describe())
        print(f"  When you have sent it:  python outreach.py --sent {approach.key}")
        print("")

    if leads:
        print(f"{len(leads)} further lead(s) need a search — run with --leads.")
    return 1 if drafted or leads else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=str(CONFIG))
    parser.add_argument("--template", action="store_true",
                        help="print a config to fill in")
    parser.add_argument("--leads", action="store_true",
                        help="only the businesses somebody has to go and search for")
    parser.add_argument("--searched", metavar="KEY",
                        help="record what you found when you searched for this business")
    parser.add_argument("--url", default="", help="with --searched: the site you found")
    parser.add_argument("--none", action="store_true",
                        help="with --searched: you looked and there is no website")
    parser.add_argument("--by", default="", help="with --searched: who looked")
    parser.add_argument("--suppress", nargs=2, metavar=("KEY", "REASON"),
                        help="never contact this business again")
    parser.add_argument("--sent", metavar="KEY",
                        help="record that you sent the draft for this business")
    args = parser.parse_args(argv)

    if args.template:
        print(json.dumps(TEMPLATE, indent=2))
        return 0

    if args.searched:
        if not args.by:
            print("--searched needs --by naming who looked. Nothing in this repository "
                  "can search the web, so this is the record of a person doing it.")
            return 2
        if not args.url and not args.none:
            print("--searched needs either --url or --none. 'I looked and found nothing' "
                  "is a finding and unlocks a draft; leaving it blank is not.")
            return 2
        searches = SearchLog.load(SEARCHES)
        try:
            searches.record(args.searched, website=args.url, checked_by=args.by)
            searches.save()
        except (RuntimeError, ValueError) as error:
            print(f"REFUSED: {error}")
            return 2
        print(f"Recorded: {args.by} searched for {args.searched} and found "
              f"{args.url or 'no website'}.")
        return 0

    if args.suppress:
        listing = SuppressionList.load(SUPPRESSION)
        try:
            listing.add(args.suppress[0], args.suppress[1])
            listing.save()
        except RuntimeError as error:
            print(f"REFUSED: {error}")
            return 2
        print(f"{args.suppress[0]} will not be contacted again.")
        return 0

    if args.sent:
        log = ApproachLog.load(APPROACHES)
        try:
            log.record(args.sent, subject="sent by hand")
            log.save()
        except RuntimeError as error:
            print(f"REFUSED: {error}")
            return 2
        print(f"Recorded. {args.sent} will not be drafted again inside the cooldown.")
        return 0

    config, unreadable = load_config(Path(args.config))
    if unreadable:
        print(f"{args.config} could not be read ({unreadable}). Running anyway would "
              f"approach nobody while looking exactly like a quiet town.")
        return 2
    if not config:
        print(f"No configuration at {args.config}. Start with "
              f"`python outreach.py --template`.")
        return 2
    if not config.get("sender") or not config.get("sender_detail"):
        print("`sender` and `sender_detail` are required. An unsolicited business message "
              "must identify who is sending it, and this will not draft one that cannot.")
        return 2

    return run(config, leads_only=args.leads)


if __name__ == "__main__":
    sys.exit(main())
