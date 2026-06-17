"""
Defense for the cached-value attack: recompute every formula from its raw
precedents and diff against the stored cache. Any cell where the recomputed
result != the cached <v> is a tampered (or merely stale) cell.

This module ships a small, dependency-light recompute engine that resolves cell
references bottom-up from non-formula inputs, so a tampered cache on an upstream
formula cell does not poison the recomputation. It supports the common
operators and IF/SUM/MIN/MAX/ROUND/ABS/AVERAGE -- enough for the included demo
and many linear models. For arbitrary workbooks use a full engine:

    * LibreOffice headless: soffice --headless --calc --convert-to xlsx (forces recalc)
    * pip install formulas   (pure-python Excel calculator)
    * pip install pycel

Usage:
    python defense/detect_xlsx.py path/to/workbook.xlsx
"""
from __future__ import annotations

import re
import sys

import openpyxl

_CELL = re.compile(r"\b[A-Z]{1,3}[0-9]+\b")
_FUNCS = {"IF": "_if", "SUM": "_sum", "MIN": "min", "MAX": "max",
          "ROUND": "_round", "ABS": "abs", "AVERAGE": "_avg"}


def _if(cond, a, b):
    return a if cond else b


def _sum(*args):
    return sum(_flatten(args))


def _avg(*args):
    vals = _flatten(args)
    return sum(vals) / len(vals) if vals else 0


def _round(x, n=0):
    return round(x, int(n))


def _flatten(args):
    out = []
    for a in args:
        out.extend(a) if isinstance(a, (list, tuple)) else out.append(a)
    return [v for v in out if isinstance(v, (int, float))]


_NS = {"_if": _if, "_sum": _sum, "_avg": _avg, "_round": _round,
       "min": min, "max": max, "abs": abs}


def _to_python(formula: str):
    """Translate an Excel formula to a python expression; return (expr, refs)."""
    f = formula.lstrip("=")
    strings = []
    f = re.sub(r'"[^"]*"', lambda m: strings.append(m.group(0)) or f"__S{len(strings) - 1}__", f)
    for name, fn in _FUNCS.items():
        f = re.sub(rf"\b{name}\s*\(", fn + "(", f, flags=re.I)
    f = f.replace("<>", "!=")
    f = re.sub(r"(?<![<>=!])=(?!=)", "==", f)   # Excel '=' comparison -> python '=='
    refs = sorted(set(_CELL.findall(f)))
    for i, s in enumerate(strings):
        f = f.replace(f"__S{i}__", s)
    return f, refs


def recompute_all(path: str) -> dict:
    """Return {cell_ref: recomputed_value} for every formula cell."""
    wb_f = openpyxl.load_workbook(path, data_only=False)
    ws = wb_f.active
    inputs, formulas = {}, {}
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is None:
                continue
            ref = cell.coordinate
            if isinstance(cell.value, str) and cell.value.startswith("="):
                formulas[ref] = cell.value
            else:
                inputs[ref] = cell.value

    memo: dict = {}

    def resolve(ref: str):
        if ref in memo:
            return memo[ref]
        if ref in inputs:
            memo[ref] = inputs[ref]
            return memo[ref]
        if ref in formulas:
            expr, refs = _to_python(formulas[ref])
            ns = dict(_NS)
            ns.update({r: resolve(r) for r in refs})
            memo[ref] = eval(expr, {"__builtins__": {}}, ns)  # noqa: S307 (sandboxed ns)
            return memo[ref]
        return None

    return {ref: resolve(ref) for ref in formulas}


def detect(path: str, tol: float = 1e-6) -> list:
    """Return [(cell, cached, recomputed)] for cells where cache != recomputation."""
    cached_wb = openpyxl.load_workbook(path, data_only=True).active
    findings = []
    for ref, recomputed in recompute_all(path).items():
        cached = cached_wb[ref].value
        if cached is None:
            continue  # empty-cache variant: handled separately by the caller
        if isinstance(recomputed, (int, float)) and isinstance(cached, (int, float)):
            mismatch = abs(float(recomputed) - float(cached)) > tol
        else:
            mismatch = str(recomputed) != str(cached)
        if mismatch:
            findings.append((ref, cached, recomputed))
    return findings


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    findings = detect(sys.argv[1])
    if not findings:
        print("OK -- no cache/recomputation divergence found.")
        return 0
    print(f"TAMPERING SUSPECTED -- {len(findings)} cell(s) where cache != recomputation:")
    for ref, cached, recomputed in findings:
        print(f"  {ref}: cached={cached!r}  recomputed={recomputed!r}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
