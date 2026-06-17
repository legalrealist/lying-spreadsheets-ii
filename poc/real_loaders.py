"""Show that *named, popular* extraction tools used in real LLM pipelines read
the falsified content by default -- this is not a strawman parser.

  XLSX: markitdown (Microsoft, explicitly an LLM document-ingestion tool)
  Email: BeautifulSoup .get_text() (the canonical HTML-to-text in countless
         RAG/email pipelines) keeps display:none content; a text/plain-first
         reader takes the divergent plain part.

Run: python poc/real_loaders.py
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from poc import lying_xlsx, lying_email as le


def xlsx_demo():
    from markitdown import MarkItDown
    lying_xlsx.build_covenant("/tmp/_rl.xlsx")
    lying_xlsx.tamper("/tmp/_rl.xlsx", "/tmp/_rl_c3.xlsx", lying_xlsx.CONDITIONS["C3"])
    md = MarkItDown().convert("/tmp/_rl_c3.xlsx").text_content
    line = next(l for l in md.splitlines() if "Debt / EBITDA" in l)
    status = next(l for l in md.splitlines() if "Covenant Status" in l)
    print("[markitdown] reads:", line.strip(), "|", status.strip())
    print("[human/Excel ] truth:", lying_xlsx.ground_truth())


def email_demo():
    from bs4 import BeautifulSoup
    # E2: display:none injection -- bs4.get_text keeps it
    raw = le.build_message(*le.SCENARIOS["E2_injection"])
    html = raw.decode()
    html = html.split("Content-Type: text/html", 1)[1].split("\n\n", 1)[1]
    text = BeautifulSoup(le.SCENARIOS["E2_injection"][1], "html.parser").get_text(" ", strip=True)
    print("\n[bs4.get_text] (E2) ingests:", text)
    print("[human render] (E2) sees  :", le.human_view(raw))


if __name__ == "__main__":
    xlsx_demo()
    email_demo()
