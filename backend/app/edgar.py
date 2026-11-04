"""SEC EDGAR access: ticker -> CIK -> most recent 10-K / 10-Q primary documents, split into pages."""
import re
import warnings

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Inline-XBRL filings are XHTML; parsing them as HTML is intended.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from app.config import EDGAR_USER_AGENT

_HEADERS = {"User-Agent": EDGAR_USER_AGENT, "Accept-Encoding": "gzip, deflate"}
# Filings mark printed page boundaries with CSS page breaks; split there to recover page numbers.
_PAGE_BREAK_RE = re.compile(
    r"<[^>]+(?:page-break-(?:before|after)|break-(?:before|after))\s*:\s*(?:always|page)[^>]*>", re.IGNORECASE
)


def _get(url: str) -> httpx.Response:
    resp = httpx.get(url, headers=_HEADERS, timeout=60, follow_redirects=True)
    resp.raise_for_status()
    return resp


def cik_for(ticker: str) -> int:
    for row in _get("https://www.sec.gov/files/company_tickers.json").json().values():
        if row["ticker"].upper() == ticker:
            return int(row["cik_str"])
    raise LookupError(f"Ticker '{ticker}' not found in SEC company list")


def latest_filings(cik: int, forms=("10-K", "10-Q")) -> list[dict]:
    recent = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").json()["filings"]["recent"]
    found: dict[str, dict] = {}
    for i, form in enumerate(recent["form"]):
        if form in forms and form not in found:
            accession = recent["accessionNumber"][i]
            found[form] = {
                "form": form,
                "accession": accession,
                "filing_date": recent["filingDate"][i],
                "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/"
                       f"{recent['primaryDocument'][i]}",
            }
    return [found[f] for f in forms if f in found]


def pages(url: str) -> list[str]:
    """Plain text of each page of a filing document (index 0 = page 1)."""
    out = []
    for fragment in _PAGE_BREAK_RE.split(_get(url).text):
        soup = BeautifulSoup(fragment, "lxml")
        for hidden in soup.find_all(["ix:header", "script", "style"]):
            hidden.decompose()
        out.append(re.sub(r"\s+", " ", soup.get_text(" ")).strip())
    return out
