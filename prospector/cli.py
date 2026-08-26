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

from prospector import (browser, cascade, case as case_mod, condition as condition_mod,
                        contacts as contacts_mod, costs as costs_mod, dossier,
                        images as images_mod, presence as presence_mod, standard,
                        webatron)
from prospector.business import Business, Fact
from prospector.countries import COUNTRY_KNOWN, Country, from_tags, lookup
from prospector.countries import UNKNOWN as COUNTRY_UNKNOWN
from prospector.locales import LANGUAGE_AVAILABLE, choose
from prospector.history import History, Run
from prospector.seen import Register
from prospector.sources import overpass
from prospector.states import (COULD_NOT_LOOK, COULD_NOT_LOOK_FOR_IMAGES, LOOKED,
                               NO_SITE_FOUND, NO_SITE_LISTED, SITE_LISTED, SITE_REACHED)

#: Refused as an operator name, in the parent repository's list and for its reason: the
#: sample page is signed, the signature is an attribution to a person, and a person is the
#: only thing that can stand over an approach to a stranger's business.
AUTOMATION_PREFIXES = ("agent:", "ai:", "model:", "automation:", "bot:", "system:")

#: And the name of this package's own agent, because the temptation is real once it has
#: one. Webatron assembles the briefing; a person signs the page and sends the mail.
REFUSED_OPERATORS = ("webatron", "prospector")


@dataclass
class Tally:
    briefings: list = field(default_factory=list)
    prepared: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    indeterminate: list[str] = field(default_factory=list)
    unrecorded: list[str] = field(default_factory=list)


def _check_condition(url: str, *, fetch: bool, capture=None) -> condition_mod.Condition | None:
    if not fetch:
        return condition_mod.Condition(
            condition_mod.UNDETERMINED, url=url,
            reason="--no-fetch was passed, so no site was assessed")
    return condition_mod.assess(url, capture=capture)


def _capture_site(url: str, identity: str, args, out_dir: Path):
    """A phone-sized render of their site, when a browser is available and wanted.

    The screenshot is the pitch and the measurements are the three criteria markup cannot
    answer, so this is worth a browser launch per business. It is skipped rather than
    faked when Playwright is not installed, and the run says so once.
    """

    if args.browser == "never" or not args.fetch or not url:
        return None
    ok, _ = browser.available()
    if not ok:
        return None
    return browser.capture(url, out_path=out_dir / "shots" / f"{dossier.slug(identity)}.png")


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


def _country_for(business: Business, discovery, args) -> Country:
    """The business's own tag first, then the area's ISO code, then what you passed.

    In that order because they are increasingly coarse. `addr:country` on the shop is about
    the shop; the area's code is about the area, which is right until a run spans a border;
    and `--country` is about the whole run, which is a statement by you rather than
    evidence and is therefore the fallback rather than the override.
    """

    from_business = from_tags((business.raw or {}).get("tags") or {})
    if from_business.status == COUNTRY_KNOWN:
        return from_business
    if discovery.country.status == COUNTRY_KNOWN:
        return discovery.country
    if args.country:
        return lookup(args.country, basis="--country, which you asserted")
    return COUNTRY_UNKNOWN


def _brief(business, presence, condition, decision, folder, language, operator, costing):
    """Assemble everything Webatron has to say about one business, and write the briefing.

    The two reports come off disk rather than being recomputed, so the case is made from
    the same measurements the dossier recorded. A case built from a fresh assessment could
    disagree with `EVIDENCE.md` and there would be no way to tell which was right.
    """

    import json

    their_report = getattr(condition, "report", None)
    our_report = None
    try:
        evidence = json.loads((folder / "evidence.json").read_text(encoding="utf-8"))
        our_report = standard.rehydrate(evidence.get("sample_standard"))
        if their_report is None:
            their_report = standard.rehydrate(evidence.get("standard"))
    except (OSError, ValueError):
        pass

    prepared = webatron.Prepared(
        identity=business.identity, name=business.name_in(language.locale.code).value,
        folder=folder, contacts=contacts_mod.assemble(business),
        case=case_mod.build(
            their_report, our_report,
            has_site=presence.status not in (NO_SITE_FOUND, NO_SITE_LISTED),
            established_absence=presence.may_claim_no_website,
            no_site_reason=("a search found no website for this business"
                            if presence.may_claim_no_website else
                            "no website is listed for them in the public directories, "
                            "which is not the same as them having none")),
        presence_status=presence.status, language=language.locale.code,
        language_reviewed=language.locale.reviewed,
        unknowns=tuple(f.detail for f in getattr(condition, "findings", ())
                       if f.code == "INDETERMINATE"))
    webatron.write_briefing(prepared, operator=operator, costing=costing, folder=folder)
    return prepared


def run(args: argparse.Namespace, stream=None, errors=None) -> int:
    out = stream or sys.stdout
    err = errors or sys.stderr
    operator = args.operator.strip()
    lowered = operator.lower()
    if lowered in REFUSED_OPERATORS or any(lowered.startswith(prefix)
                                           for prefix in AUTOMATION_PREFIXES):
        print(f"REFUSED: --operator {operator!r} names an automation. A sample site carries "
              f"a real business's name and must be signed by the person who stands over "
              f"sending it.", file=err)
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

    print(discovery.describe(), file=out)
    if discovery.status != LOOKED:
        # Nothing below this line would be true, so nothing below this line runs. The run
        # is still recorded: a history with only the successful scans in it makes a flaky
        # source look reliable and hides "the scan of Mayo died" behind "Mayo was quiet".
        History(Path(args.history)).record(Run(
            area=args.area, started=discovery.at, finished=discovery.at,
            outcome=discovery.status, operator=operator))
        return 1

    register = Register(Path(args.register))
    out_dir = Path(args.out) / dossier.slug(args.area)
    tally = Tally()
    started_at = discovery.at
    rates, currency, costs_note = costs_mod.load(args.costs)
    costing = costs_mod.cost_of_one_site(rates, currency=currency)

    for business in discovery.businesses:
        label = f"{business.name.value} ({business.identity})"
        sighting = register.check(business.identity)
        presence = presence_mod.assess(business)
        condition = None
        if presence.status in (SITE_LISTED, SITE_REACHED) and not presence.is_social_only:
            shot = _capture_site(presence.url, business.identity, args, out_dir)
            condition = _check_condition(presence.url, fetch=args.fetch, capture=shot)
        country = _country_for(business, discovery, args)
        language = choose(args.language, country_languages=country.languages,
                          country=country.name)
        decision = cascade.with_language(
            cascade.decide(business, sighting, presence, condition,
                           prepare_again=args.again), language)

        if decision.status == cascade.PREPARE:
            if args.dry:
                tally.prepared.append(f"{label} [{language.locale.code}] — "
                                      f"{decision.reason} (dry run, nothing written)")
                continue
            image_set = _images_for(business, presence, args)
            folder = dossier.write(business, presence, condition, decision,
                                   out_dir=out_dir, operator=operator,
                                   images=image_set, fetch_images=args.fetch,
                                   locale=language.locale, country=country,
                                   shoot_sample=args.browser != "never")
            if not register.record(business.identity):
                tally.unrecorded.append(label)
            unreviewed = "" if language.locale.reviewed else "  UNREVIEWED TRANSLATION"
            tally.prepared.append(f"{label} [{language.locale.code}] -> {folder}"
                                  f"{unreviewed}")
            tally.briefings.append(_brief(business, presence, condition, decision, folder,
                                          language, operator, costing))
        elif decision.status == cascade.REFUSED:
            tally.refused.append(f"{label} — [{decision.stage}] {decision.reason}")
        else:
            tally.indeterminate.append(f"{label} — [{decision.stage}] {decision.reason}")

    _report(discovery, tally, out_dir, dry=args.dry, out=out)
    if not args.dry:
        recorded = History(Path(args.history)).record(Run(
            area=args.area, started=started_at, finished=discovery.at,
            prepared=len(tally.prepared), refused=len(tally.refused),
            indeterminate=len(tally.indeterminate), outcome=discovery.status,
            digest=str(out_dir / webatron.DIGEST), operator=operator))
        if not recorded:
            print(f"HISTORY        NOT RECORDED — {args.history} could not be written, so "
                  f"this run will not appear in what has been scanned", file=out)
        digest = webatron.write_digest(
            tally.briefings, out_dir=out_dir, operator=operator, costing=costing,
            area=args.area, refused=tally.refused, indeterminate=tally.indeterminate)
        print(f"{webatron.NAME:14} {digest}", file=out)
        if costs_note:
            print(f"{'':14} costs: {costs_note}", file=out)
        if args.notify_command:
            sent, how = webatron.notify(args.notify_command, digest)
            print(f"{'NOTIFY':14} {'sent' if sent else 'NOT SENT — ' + how}", file=out)
    return 0


def _report(discovery, tally: Tally, out_dir: Path, *, dry: bool, out=None) -> None:
    out = out or sys.stdout
    print(file=out)
    ok, reason = browser.available()
    if ok:
        print("BROWSER        available: mobile criteria were measured in a phone-sized "
              "window, and screenshots were taken", file=out)
    else:
        # Said once, loudly, because every mobile criterion below is markup-only and that
        # is a weaker claim than the report would otherwise look like it is making.
        print(f"BROWSER        NOT AVAILABLE — {reason}", file=out)
        print("               Mobile checks are markup-only for this run. That is not "
              "the same as them passing.", file=out)
    print(f"PREPARED       {len(tally.prepared)}", file=out)
    for line in tally.prepared:
        print(f"  {line}", file=out)
    print(f"REFUSED        {len(tally.refused)}   (a stage said no, and named itself)", file=out)
    for line in tally.refused:
        print(f"  {line}", file=out)
    print(f"INDETERMINATE  {len(tally.indeterminate)}   (could not be evaluated — NOT a "
          f"refusal, and NOT nothing)", file=out)
    for line in tally.indeterminate:
        print(f"  {line}", file=out)
    if tally.unrecorded:
        # Loud, because the consequence lands next week rather than now: an unrecorded
        # preparation is a business this will prepare and approach for a second time.
        print(f"\nNOT RECORDED IN THE REGISTER  {len(tally.unrecorded)}", file=out)
        print("  These were prepared and the register could not be written, so a later "
              "run will prepare them again:", file=out)
        for line in tally.unrecorded:
            print(f"  {line}", file=out)
    print(file=out)
    if dry:
        print("Dry run: nothing was written and nothing was recorded.", file=out)
    else:
        print(f"Dossiers in {out_dir}. Nothing has been sent to anybody — each folder "
              f"holds a draft note for you to read, edit and send yourself.", file=out)


def main(argv: list[str] | None = None, stream=None, errors=None) -> int:
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
    parser.add_argument("--history", default=str(History.__init__.__defaults__[0]),
                        help="where completed runs are recorded, so a scanning cadence can "
                             "be decided from what actually happened rather than guessed "
                             "in advance")
    parser.add_argument("--costs", default=str(costs_mod.CONFIG),
                        help="rates for the costing on every briefing. Anything absent is "
                             "UNPRICED rather than zero, so the first run tells you what "
                             "you have not decided. See costs.example.json")
    parser.add_argument("--notify-command", default="",
                        help="a command to hand the digest to, with {digest} substituted. "
                             "There is no mail path in this package; this runs whatever "
                             "you already use, and reports its exit code rather than "
                             "swallowing it")
    parser.add_argument("--browser", choices=("auto", "never"), default="auto",
                        help="open each site in a phone-sized browser to measure what "
                             "actually renders and to screenshot it beside the sample. "
                             "'auto' uses Playwright where it is installed and says so "
                             "when it is not; the mobile criteria it decides are never "
                             "assumed to pass")
    parser.add_argument("--language", default="",
                        help="the language to build in, e.g. fr, de, ga. Omitted, it is "
                             "taken from the country; a language this package has no "
                             "strings for refuses rather than falling back to English")
    parser.add_argument("--country", default="",
                        help="ISO 3166-1 alpha-2 code, e.g. PT. Only used when neither the "
                             "business nor the area says which country it is in; it "
                             "decides the language and which sending rules are printed")
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
    return run(parser.parse_args(argv), stream=stream, errors=errors)
