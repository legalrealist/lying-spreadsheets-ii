"""
Defense for the email multipart attack: extract both text/plain and text/html
(stripping display:none / off-screen content), normalize, and flag material
divergence between what the pipeline reads and what the human sees.

Usage:
    python defense/detect_email.py path/to/message.eml
"""
from __future__ import annotations

import re
import sys
from email import message_from_bytes
from email.policy import default

# Tokens worth comparing across the two readings: money, account/routing
# numbers, durations, percentages, and capitalized terms.
_SIGNAL = re.compile(
    r"\$[\d,]+(?:\.\d+)?"            # money
    r"|\b\d{3,}[-\d]*\b"             # account / routing / long numbers
    r"|\b\d+\s?(?:weeks?|days?|months?|years?)\b"  # durations
    r"|\b\d+(?:\.\d+)?%\b",         # percentages
    re.I,
)
_HIDDEN = re.compile(r'<[^>]*style="[^"]*display\s*:\s*none[^"]*"[^>]*>.*?</[^>]+>', re.I | re.S)


def _strip_html(html: str, drop_hidden: bool) -> str:
    if drop_hidden:
        html = _HIDDEN.sub("", html)
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _signals(text: str) -> set:
    return {m.group(0).replace(" ", "").lower() for m in _SIGNAL.finditer(text)}


def detect(raw: bytes) -> dict:
    """Return a report dict; `divergent` is True if the readings disagree."""
    msg = message_from_bytes(raw, policy=default)
    plain_part = msg.get_body(preferencelist=("plain",))
    html_part = msg.get_body(preferencelist=("html",))
    plain = plain_part.get_content().strip() if plain_part else ""
    html_raw = html_part.get_content() if html_part else ""

    human = _strip_html(html_raw, drop_hidden=True)     # what the human sees
    hidden_present = bool(_HIDDEN.search(html_raw))

    report = {
        "plain_signals": _signals(plain),
        "human_signals": _signals(human),
        "hidden_content": hidden_present,
    }
    # Divergent if the pipeline-visible signals differ from the human-visible
    # signals, or if any display:none content exists at all.
    report["divergent"] = (
        report["plain_signals"] != report["human_signals"] or hidden_present
    )
    return report


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    with open(sys.argv[1], "rb") as fh:
        report = detect(fh.read())
    if not report["divergent"]:
        print("OK -- text/plain and text/html agree; no hidden content.")
        return 0
    print("DIVERGENCE SUSPECTED:")
    print(f"  pipeline (text/plain) signals: {sorted(report['plain_signals'])}")
    print(f"  human (rendered HTML) signals: {sorted(report['human_signals'])}")
    if report["hidden_content"]:
        print("  display:none content present (visible to an HTML-stripping pipeline, not the human)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
