#!/usr/bin/env python3
"""Inline data/*.json into src/template.html and write index.html."""
import os
from datetime import date

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
read = lambda *p: open(os.path.join(root, *p)).read()
html = read("src", "template.html")
for marker, name in [("/*DATA*/", "bls.json"), ("/*STATES*/", "states.json"), ("/*OCC*/", "occupations.json")]:
    assert marker in html, f"{marker} missing from template"
    html = html.replace(marker, read("data", name))
today = date.today()
html = html.replace('const RETRIEVED = "November 16, 2026";',
                    f'const RETRIEVED = "{today:%B} {today.day}, {today.year}";')
open(os.path.join(root, "index.html"), "w").write(html)
print("Built index.html")
