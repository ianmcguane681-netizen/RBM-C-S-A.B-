"""The vocabulary. Every stage of this pipeline has a third state, and each one names a
different reason the obvious answer is not available.

The rule inherited from the parent repository: **a value meaning *not found* or *unknown*
must never render as *not there*.** In this domain that rule has teeth, because the output
is not a number on a dashboard — it is an email to a real business. "You have no website"
sent to a shop whose website merely was not in the directory is the same defect as a stock
screener reporting a 404 as "does not report a share count", except a person reads this one
and forms a view about the sender.

So the states are deliberately more finely divided than a first pass would suggest.

## The listing says what the listing says

    SITE_LISTED        the directory carries a website for this business
    NO_SITE_LISTED     the directory carries none. This is a fact about the DIRECTORY
    DIRECTORY_SILENT   the business was not found in the directory at all

`NO_SITE_LISTED` is the one people get wrong. OpenStreetMap not knowing a website is
extremely common and is not evidence that none exists; it is a gap in a volunteer dataset.
Treating it as "no website" is what produces the confidently wrong pitch.

## Only an independent look can promote that to a claim about the business

    SITE_REACHED       something answered, and it belongs to this business
    NO_SITE_FOUND      looked in the places a site would be, and there was nothing
    COULD_NOT_LOOK     the look itself failed: network, timeout, blocked, no budget

## What was found, if anything was

    SERVICEABLE        nothing disqualifying was found. NOT a judgement that it is good
    DEFICIENT          a specific, stated, checkable defect was found
    UNDETERMINED       the page could not be assessed. Never merged into either of the above

`SERVICEABLE` is worded to resist the thing this whole design refuses. There is no such
thing as a machine-checkable "good website", so the cascade only ever establishes that a
named defect is present or that no named defect was found. The second is not praise and
must never be reported as one.

## Whether this business has been put in front of you before

    NEW                no record of this business having been prepared
    SEEN_BEFORE        prepared on these dates, this many times
    UNCHECKED          the register could not be read. Never NEW

## What was produced

    PREPARED           a dossier exists on disk and a person can read it
    NOT_PREPARED       the cascade refused, and which stage refused is named
    PREPARATION_FAILED the cascade passed and the build did not. A bug, not a refusal
"""
from __future__ import annotations

# Listing-level.
SITE_LISTED = "SITE_LISTED"
NO_SITE_LISTED = "NO_SITE_LISTED"
DIRECTORY_SILENT = "DIRECTORY_SILENT"

# Independent look.
SITE_REACHED = "SITE_REACHED"
NO_SITE_FOUND = "NO_SITE_FOUND"
COULD_NOT_LOOK = "COULD_NOT_LOOK"

# Condition.
SERVICEABLE = "SERVICEABLE"
DEFICIENT = "DEFICIENT"
UNDETERMINED = "UNDETERMINED"

# Register.
NEW = "NEW"
SEEN_BEFORE = "SEEN_BEFORE"
UNCHECKED = "UNCHECKED"

# Outcome of a run over one business.
PREPARED = "PREPARED"
NOT_PREPARED = "NOT_PREPARED"
PREPARATION_FAILED = "PREPARATION_FAILED"

# Discovery, at the level of a whole area.
LOOKED = "LOOKED"
AREA_UNKNOWN = "AREA_UNKNOWN"
SOURCE_UNREADABLE = "SOURCE_UNREADABLE"

# Images. `NO_IMAGE_FOUND` and `COULD_NOT_LOOK_FOR_IMAGES` are kept apart for the usual
# reason and one specific to this stage: a page built with no photograph because none was
# licensable is a decision, and a page built with no photograph because the search failed
# is a page that should have been built later.
IMAGES_FOUND = "IMAGES_FOUND"
NO_IMAGE_FOUND = "NO_IMAGE_FOUND"
COULD_NOT_LOOK_FOR_IMAGES = "COULD_NOT_LOOK_FOR_IMAGES"

#: Where a photograph came from, which decides what the page is obliged to say about it.
SUBJECT_OWN = "SUBJECT_OWN"
LICENSED_STOCK = "LICENSED_STOCK"
#: Sent by the business itself after the first approach. The only provenance with no
#: question attached to it: they own it and they handed it over.
SUBJECT_SUPPLIED = "SUBJECT_SUPPLIED"

# What the business sent back, if anything.
SUPPLIED = "SUPPLIED"
NOTHING_SUPPLIED = "NOTHING_SUPPLIED"
HANDOVER_UNREADABLE = "HANDOVER_UNREADABLE"

# Verification of a page against the evidence behind it.
VERIFIED = "VERIFIED"
UNSOURCED_CLAIMS = "UNSOURCED_CLAIMS"
COULD_NOT_VERIFY = "COULD_NOT_VERIFY"
