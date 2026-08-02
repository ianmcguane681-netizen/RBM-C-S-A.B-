"""Run the filing gates against one company and print what its own filings establish.

    python check_stock.py AAPL

No API key. EDGAR asks only that a client identify itself, which `EdgarClient` does.

This is the fast path, the equity twin of `check_token.py`: the facts, cited to the
accession number that produced them, with no decision record and no verdict. Its job is to
tell you what the company filed and where the filings disagree with each other.
"""
from __future__ import annotations

import sys

from connectors.edgar import NOT_REPORTED, REPORTED, EdgarClient

# Several tags per quantity, because filers tag the same idea differently and asking for
# one would report NOT_REPORTED about the tag while implying it about the company.
CONCEPTS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "net income": ["NetIncomeLoss"],
    "total assets": ["Assets"],
    "total liabilities": ["Liabilities"],
    "long-term debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "shares outstanding": [
        "CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding",
    ],
    "diluted shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}


def main(ticker: str) -> int:
    client = EdgarClient()
    cik = client.cik_for_ticker(ticker)
    print(f"{ticker.upper()} -> CIK {cik}   source: SEC EDGAR, no key required\n")

    total_revised = 0
    for label, tags in CONCEPTS.items():
        series = client.first_reported(cik, tags)
        print(f"SG-01/SG-02  {label}")
        if series.status != REPORTED:
            print(f"   {series.describe()}\n")
            continue

        latest = series.latest_annual()
        if latest:
            print(f"   {latest.value:>22,.0f} {latest.unit}   [{latest.cite()}]")
        else:
            print(f"   reported, but no annual span found among {len(series.durations)} spans")

        revised = series.revised_durations()
        total_revised += len(revised)
        if revised:
            print(f"   {len(revised)} span(s) filed at more than one value:")
            for duration, filings in list(revised.items())[:2]:
                print(f"      {duration}")
                for filing in filings:
                    print(f"        {filing.value:>20,.0f}  {filing.form:<7} filed {filing.filed}")
        print()

    print("=" * 72)
    if total_revised:
        print(f"{total_revised} reporting span(s) above were filed at more than one value.")
        print("A restated figure and the original are two different facts. Neither has been")
        print("chosen here, and a ratio mixing them measures the correction, not the business.")
    print("Every figure is cited to the filing that produced it and is retrievable by anyone.")
    print("None of it says whether to buy. This board has no view on price.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
