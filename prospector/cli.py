"""`python -m prospector --area "County Donegal" --operator "Ian McGuane"`.

The run report is the point of this file. Anyone can print a list of prospects; the thing
that makes the output trustworthy enough to act on is that it never merges "looked and
found nothing" with "could not look", at any level — not for the county, not for a single
business, not for a single website. Read the summary from the bottom up: the counts that
matter most are the indeterminate ones, because those are the businesses this run has no
opinion about and would have silently dropped if it were built the usual way.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from prospector import (cascade, condition as condition_mod, dossier, images as images_mod,
                        presence as presence_mod)
from prospector.business import Business, Fact
from prospector.seen import Register
from prospector.sources import overpass
from prospector.states import (COULD_NOT_LOOK, COULD_NOT_LOOK_FOR_IMAGES, LOOKED,
                               NO_SITE_FOUND, SITE_LISTED, SITE_REACHED)

#: Refused as an operator name, in the parent repository's list and for its reason: the
#: sample page is signed, the signature is an attribution to a person, and a person is the
#: only thing that can stand over an approach to a stranger's business.
AUTOMATION_PREFIXES = ("agent:", "ai:", "model:", "automation:", "bot:", "system:")


@dataclass
class Tally:
    prepared: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    indeterminate: list[str] = field(default_factory=list)
    unrecorded: list[str] = field(default_factory=list)


def _check_condition(url: str, *, fetch: bool) -> condition_mod.Condition | None:
    if not fetch:
        return condition_mod.Condition(
            condition_mod.UNDETERMINED, url=url,
            reason="--no-fetch was passed, so no site was assessed")
    return condition_mod.assess(url)


def _images_for(business: Business, presence, args) -> images_mod.ImageSet:
    """Their own photographs first, stock second, and nothing at all if asked.

    Their own is not merely preferred, it is a different product: a page showing a business
    its own shopfront is the version that gets a reply. Stock is the fallback that keeps a
    page from looking like a wireframe, and it is labelled on the page as what it is.
    """

    if args.images == "none" or not args.fetch:
        return images_mod.ImageSet(
            COULD_NOT_LOOK_FOR_IMAGES,
            reason=("--images none was passed" if args.images == "none"
                    else "--no-fetch was passed, so no image source was contacted"))
    sets = []
    if args.images in ("both", "subject") and presence.url and not presence.is_social_only:
        sets.append(images_mod.from_subject(presence.url, limit=args.image_count))
    if args.images in ("both", "stock"):
        city = business.get("city")
        query = business.kind.value.replace("_", " ")
        if isinstance(city, Fact):
            # The trade alone; the town is deliberately NOT in the query. A stock photo
            # found by searching "barber Letterkenny" is still not Letterkenny, and a
            # picture that looks local is a stronger false claim than one that does not.
            pass
        sets.append(images_mod.Openverse().search(query, limit=args.image_count))
    if not sets:
        return images_mod.ImageSet(COULD_NOT_LOOK_FOR_IMAGES,
                                   reason=f"--images {args.images} selected no source for "
                                          f"this business")
    return images_mod.gather(*sets)


def run(args: argparse.Namespace) -> int:
    operator = args.operator.strip()
    lowered = operator.lower()
    if any(lowered.startswith(prefix) for prefix in AUTOMATION_PREFIXES):
        print(f"REFUSED: --operator {operator!r} names an automation. A sample site carries "
              f"a real business's name and must be signed by the person who stands over "
              f"sending it.", file=sys.stderr)
        return 2

    if args.from_file:
        # Reads a saved Overpass response. The point is a run that exercises every stage
        # on a machine that cannot reach the directory — including this one.
        import json
        raw = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
        at = overpass._now()
        found = [b for b in (overpass.to_business(e, at=at)
                             for e in raw.get("elements", [])) if b]
        discovery = overpass.Discovery(LOOKED, args.area, tuple(found),
                                       endpoint=f"file:{args.from_file}")
    else:
        discovery = overpass.discover(args.area, limit=args.limit,
                                      transport=overpass._Transport(args.endpoint))

    print(discovery.describe())
    if discovery.status != LOOKED:
        # Nothing below this line would be true, so nothing below this line runs.
        return 1

    register = Register(Path(args.register))
    out_dir = Path(args.out) / dossier.slug(args.area)
    tally = Tally()

    for business in discovery.businesses:
        label = f"{business.name.value} ({business.identity})"
        sighting = register.check(business.identity)
        presence = presence_mod.assess(business)
        condition = None
        if presence.status in (SITE_LISTED, SITE_REACHED) and not presence.is_social_only:
            condition = _check_condition(presence.url, fetch=args.fetch)
        decision = cascade.decide(business, sighting, presence, condition,
                                  prepare_again=args.again)

        if decision.status == cascade.PREPARE:
            if args.dry:
                tally.prepared.append(f"{label} — {decision.reason} (dry run, nothing written)")
                continue
            image_set = _images_for(business, presence, args)
            folder = dossier.write(business, presence, condition, decision,
                                   out_dir=out_dir, operator=operator,
                                   images=image_set, fetch_images=args.fetch)
            if not register.record(business.identity):
                tally.unrecorded.append(label)
            tally.prepared.append(f"{label} -> {folder}")
        elif decision.status == cascade.REFUSED:
            tally.refused.append(f"{label} — [{decision.stage}] {decision.reason}")
        else:
            tally.indeterminate.append(f"{label} — [{decision.stage}] {decision.reason}")

    _report(discovery, tally, out_dir, dry=args.dry)
    return 0


def _report(discovery, tally: Tally, out_dir: Path, *, dry: bool) -> None:
    print()
    print(f"PREPARED       {len(tally.prepared)}")
    for line in tally.prepared:
        print(f"  {line}")
    print(f"REFUSED        {len(tally.refused)}   (a stage said no, and named itself)")
    for line in tally.refused:
        print(f"  {line}")
    print(f"INDETERMINATE  {len(tally.indeterminate)}   (could not be evaluated — NOT a "
          f"refusal, and NOT nothing)")
    for line in tally.indeterminate:
        print(f"  {line}")
    if tally.unrecorded:
        # Loud, because the consequence lands next week rather than now: an unrecorded
        # preparation is a business this will prepare and approach for a second time.
        print(f"\nNOT RECORDED IN THE REGISTER  {len(tally.unrecorded)}")
        print("  These were prepared and the register could not be written, so a later "
              "run will prepare them again:")
        for line in tally.unrecorded:
            print(f"  {line}")
    print()
    if dry:
        print("Dry run: nothing was written and nothing was recorded.")
    else:
        print(f"Dossiers in {out_dir}. Nothing has been sent to anybody — each folder "
              f"holds a draft note for you to read, edit and send yourself.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prospector",
        description="Find businesses whose web presence is absent or broken, and build "
                    "each one a sample site out of publicly listed facts.")
    parser.add_argument("--area", required=True,
                        help="the area name as OpenStreetMap spells it, e.g. "
                             "'County Donegal', 'Ireland', 'Letterkenny'")
    parser.add_argument("--operator", required=True,
                        help="the person the sample pages are signed by")
    parser.add_argument("--out", default="dossiers", help="where the folders are written")
    parser.add_argument("--register", default="data/prepared.json",
                        help="the seen register, so nobody is approached twice")
    parser.add_argument("--limit", type=int, default=200,
                        help="maximum businesses to pull from the directory")
    parser.add_argument("--endpoint", default=overpass.DEFAULT_ENDPOINT,
                        help="Overpass endpoint; mirrors differ in coverage and in who "
                             "blocks them")
    parser.add_argument("--from-file", default="",
                        help="read a saved Overpass response instead of querying")
    parser.add_argument("--again", action="store_true",
                        help="prepare businesses that have been prepared before")
    parser.add_argument("--no-fetch", dest="fetch", action="store_false",
                        help="do not fetch any business's website; every site condition "
                             "becomes UNDETERMINED and nothing with a site is prepared")
    parser.add_argument("--images", choices=("both", "subject", "stock", "none"),
                        default="both",
                        help="where photographs come from: 'subject' takes them from the "
                             "business's own site with robots.txt honoured, 'stock' uses "
                             "Openverse under licences permitting commercial use and "
                             "modification, and every stock image is labelled on the page "
                             "as not being their premises")
    parser.add_argument("--image-count", type=int, default=2,
                        help="how many photographs to gather per business")
    parser.add_argument("--dry", action="store_true",
                        help="decide everything, write nothing, record nothing")
    return run(parser.parse_args(argv))
