"""Which country this business is in, what people there do business in, and the rule about
sending them an email.

Running in one country lets you keep all of this in your head. Running in several does not,
and the two things that change across a border are exactly the two that are expensive to
get wrong: the language the page speaks, and whether an unsolicited commercial email is a
normal piece of business development or a fine.

## The regimes, and why the unknown case is the strict one

The rules genuinely differ. Canada requires consent before a commercial message and treats
the absence of it as an offence; the United States allows the message and requires a way
out of it; the EU and the UK sit in between and vary by member state, with business
addresses usually treated more permissively than personal ones. So a country this table
does not know resolves to `UNKNOWN`, and `UNKNOWN` prints the strictest guidance rather
than the mildest — the same fail-toward-stopping rule the rest of the package uses, applied
where being wrong costs money rather than credibility.

**None of this is legal advice and the tool says so where it prints it.** What it is, is a
prompt to check before sending a hundred of anything, at the moment a person is holding a
hundred folders and feeling productive.
"""
from __future__ import annotations

from dataclasses import dataclass

COUNTRY_KNOWN = "COUNTRY_KNOWN"
COUNTRY_UNKNOWN = "COUNTRY_UNKNOWN"

EU_EPRIVACY = "EU_EPRIVACY"
UK_PECR = "UK_PECR"
US_CAN_SPAM = "US_CAN_SPAM"
CA_CASL = "CA_CASL"
AU_SPAM_ACT = "AU_SPAM_ACT"
UNKNOWN_REGIME = "UNKNOWN_REGIME"

REGIMES = {
    EU_EPRIVACY: (
        "EU / EEA — GDPR and the ePrivacy rules. Unsolicited commercial email to a "
        "business address is treated more permissively than to a person, and the "
        "permission varies by member state; a named individual's address at a company "
        "(joe@shop.ie) is likelier to be personal data than info@shop.ie. Whatever you "
        "send needs your identity, a reason you are writing to them specifically, and a "
        "way to tell you to stop that you then honour. Volume is what turns this from "
        "outreach into direct marketing."),
    UK_PECR: (
        "UK — PECR and UK GDPR. Corporate subscribers may be emailed without prior "
        "consent, sole traders and partnerships are treated as individuals and may not. "
        "Identify yourself, say why them, and honour an objection first time."),
    US_CAN_SPAM: (
        "United States — CAN-SPAM. Consent is not required, but the message must not "
        "mislead in its headers or subject, must be identifiable as a solicitation, must "
        "carry a valid physical postal address, and must offer an opt-out that works for "
        "30 days and is honoured within 10 business days. Per-message penalties are why "
        "the volume question matters."),
    CA_CASL: (
        "Canada — CASL, and this is the strict one. A commercial electronic message "
        "generally requires consent BEFORE it is sent; published business addresses can "
        "support implied consent only when the message relates to the recipient's role "
        "and the address carries no statement refusing such messages. Assume you need a "
        "reason you could show a regulator, per message."),
    AU_SPAM_ACT: (
        "Australia — the Spam Act. Consent is required, though publishing a work address "
        "publicly can be inferred consent for messages relevant to that role. Identify "
        "the sender and include a working unsubscribe."),
    UNKNOWN_REGIME: (
        "The country could not be established, so this prints the strict reading: assume "
        "consent is required before a commercial email, that the recipient's address is "
        "personal data, and that volume makes it direct marketing. Establish the country "
        "before sending anything at scale."),
}

#: iso -> (name, languages this package should try in order, regime)
COUNTRIES: dict[str, tuple[str, tuple[str, ...], str]] = {
    "IE": ("Ireland", ("en", "ga"), EU_EPRIVACY),
    "GB": ("the United Kingdom", ("en",), UK_PECR),
    "FR": ("France", ("fr",), EU_EPRIVACY),
    "BE": ("Belgium", ("nl", "fr"), EU_EPRIVACY),
    "NL": ("the Netherlands", ("nl",), EU_EPRIVACY),
    "DE": ("Germany", ("de",), EU_EPRIVACY),
    "AT": ("Austria", ("de",), EU_EPRIVACY),
    "CH": ("Switzerland", ("de", "fr", "it"), UNKNOWN_REGIME),
    "LU": ("Luxembourg", ("fr", "de"), EU_EPRIVACY),
    "ES": ("Spain", ("es",), EU_EPRIVACY),
    "PT": ("Portugal", ("pt",), EU_EPRIVACY),
    "IT": ("Italy", ("it",), EU_EPRIVACY),
    "MT": ("Malta", ("en",), EU_EPRIVACY),
    "CY": ("Cyprus", ("en",), EU_EPRIVACY),
    "DK": ("Denmark", ("da", "en"), EU_EPRIVACY),
    "SE": ("Sweden", ("sv", "en"), EU_EPRIVACY),
    "FI": ("Finland", ("fi", "sv", "en"), EU_EPRIVACY),
    "NO": ("Norway", ("no", "en"), EU_EPRIVACY),
    "IS": ("Iceland", ("is", "en"), EU_EPRIVACY),
    "PL": ("Poland", ("pl",), EU_EPRIVACY),
    "CZ": ("Czechia", ("cs",), EU_EPRIVACY),
    "SK": ("Slovakia", ("sk",), EU_EPRIVACY),
    "HU": ("Hungary", ("hu",), EU_EPRIVACY),
    "RO": ("Romania", ("ro",), EU_EPRIVACY),
    "BG": ("Bulgaria", ("bg",), EU_EPRIVACY),
    "GR": ("Greece", ("el",), EU_EPRIVACY),
    "HR": ("Croatia", ("hr",), EU_EPRIVACY),
    "SI": ("Slovenia", ("sl",), EU_EPRIVACY),
    "EE": ("Estonia", ("et", "en"), EU_EPRIVACY),
    "LV": ("Latvia", ("lv", "en"), EU_EPRIVACY),
    "LT": ("Lithuania", ("lt", "en"), EU_EPRIVACY),
    "US": ("the United States", ("en", "es"), US_CAN_SPAM),
    "CA": ("Canada", ("en", "fr"), CA_CASL),
    "AU": ("Australia", ("en",), AU_SPAM_ACT),
    "NZ": ("New Zealand", ("en",), AU_SPAM_ACT),
}


@dataclass(frozen=True, slots=True)
class Country:
    """Which country, how it was established, and what that implies."""

    status: str
    code: str = ""
    name: str = ""
    languages: tuple[str, ...] = ()
    regime: str = UNKNOWN_REGIME
    basis: str = ""

    @property
    def outreach_rule(self) -> str:
        return REGIMES.get(self.regime, REGIMES[UNKNOWN_REGIME])

    def describe(self) -> str:
        if self.status == COUNTRY_KNOWN:
            return (f"COUNTRY_KNOWN  {self.code} ({self.name}), {self.basis}; "
                    f"languages tried: {', '.join(self.languages) or 'none'}")
        return ("COUNTRY_UNKNOWN  neither the listing nor the area said which country this "
                "is in.\n  The language cannot be inferred and the strictest reading of "
                "the sending rules applies. Pass --country.")


UNKNOWN = Country(COUNTRY_UNKNOWN)


def lookup(code: str, *, basis: str = "") -> Country:
    """A country by ISO 3166-1 alpha-2 code, or `COUNTRY_UNKNOWN` for one not in the table.

    A code this table does not carry is not an error and not a default: the country is
    real, this package simply does not know its languages or its rules, and saying so is
    more use than guessing either.
    """

    code = (code or "").strip().upper()[:2]
    if not code:
        return UNKNOWN
    entry = COUNTRIES.get(code)
    if entry is None:
        return Country(COUNTRY_UNKNOWN, code=code,
                       basis=f"{code} is not in this package's country table")
    name, languages, regime = entry
    return Country(COUNTRY_KNOWN, code, name, languages, regime, basis or "given")


def from_tags(tags: dict) -> Country:
    """`addr:country` on the business, if the mapper filled it in. Often they did not."""

    for key in ("addr:country", "is_in:country_code", "country"):
        value = str(tags.get(key, "")).strip()
        if len(value) == 2:
            return lookup(value, basis=f"the business's {key} tag")
    return UNKNOWN


def from_area_tags(tags: dict) -> Country:
    """The country of an administrative area, from the ISO codes OSM puts on the relation.

    `ISO3166-1:alpha2` appears on countries; `ISO3166-2` appears on subdivisions and its
    first half is the country ("IE-DL" is County Donegal). Reading the second is what lets
    `--area "County Donegal"` know it is in Ireland without being told.
    """

    alpha2 = str(tags.get("ISO3166-1:alpha2") or tags.get("ISO3166-1") or "").strip()
    if len(alpha2) == 2:
        return lookup(alpha2, basis="the area's ISO 3166-1 code")
    subdivision = str(tags.get("ISO3166-2", "")).strip()
    if "-" in subdivision:
        return lookup(subdivision.split("-", 1)[0], basis="the area's ISO 3166-2 code")
    return UNKNOWN
