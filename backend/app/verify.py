"""Deterministic number check: every number in the answer must appear in a cited chunk or a quote result.

Allowed transformations are rounding and unit scaling (e.g. 391,035 million -> 391.0 billion).
Anything the model computed itself (growth rates, ratios) will not match and makes the answer unverified.
"""
import re

CITATION_RE = re.compile(r"\[(C\d+(?:\s*,\s*C\d+)*)\]")
_NUMBER_RE = re.compile(
    r"(?<![\w.])\$?\(?-?(\d[\d,]*(?:\.\d+)?)\)?%?(\s*(?:thousand|million|billion|trillion)\b)?", re.IGNORECASE
)
_IGNORE_RES = [
    CITATION_RE,
    re.compile(r"\b10-[KQ]\b"),                 # form names
    re.compile(r"^\s*\d+[.)]\s", re.MULTILINE),  # list numbering
]
_SCALES = (1, 1e-3, 1e-6, 1e-9, 1e3, 1e6, 1e9)


def cited_ids(answer: str) -> list[str]:
    ids: list[str] = []
    for group in CITATION_RE.findall(answer):
        for cid in re.split(r"\s*,\s*", group):
            if cid not in ids:
                ids.append(cid)
    return ids


def _numbers(text: str) -> list[tuple[float, int, bool, str]]:
    """(absolute value, decimal places, has scale word, raw token) for each number in text."""
    out = []
    for m in _NUMBER_RE.finditer(text):
        clean = m.group(1).replace(",", "")
        decimals = len(clean.split(".")[1]) if "." in clean else 0
        out.append((float(clean), decimals, bool(m.group(2)), m.group(0).strip()))
    return out


def _matches(value: float, decimals: int, scaled: bool, evidence: list[float]) -> bool:
    # Unit conversion is only accepted when the answer names the unit ("391.0 billion");
    # otherwise a computed figure like 2.0% could match 2024 x 0.001.
    scales = _SCALES if scaled else (1,)
    return any(round(e * s, decimals) == round(value, decimals) for e in evidence for s in scales)


def verify(answer: str, chunks: dict[str, dict], quotes: list[dict]) -> tuple[bool, list[str]]:
    """Returns (verified, problems)."""
    problems: list[str] = []
    ids = cited_ids(answer)
    unknown = [c for c in ids if c not in chunks]
    if unknown:
        problems.append(f"cites passages that were never retrieved: {unknown}")
    if chunks and not ids:
        problems.append("filings were retrieved but the answer cites none")

    # Evidence: cited chunk text and metadata (filing date, page), plus every field of each quote result.
    evidence_text = " ".join(
        f"{chunks[c]['text']} {chunks[c]['filing_date']} {chunks[c]['page']}" for c in ids if c in chunks
    )
    evidence_text += " " + " ".join(q["timestamp"] for q in quotes)
    evidence = [v for v, _, _, _ in _numbers(evidence_text)]
    for q in quotes:
        evidence += [abs(float(q[k])) for k in ("price", "change", "change_percent", "volume")]

    checked = answer
    for pattern in _IGNORE_RES:
        checked = pattern.sub(" ", checked)
    for value, decimals, scaled, token in _numbers(checked):
        if not _matches(value, decimals, scaled, evidence):
            problems.append(f"number not found in evidence: {token}")
    return not problems, problems
