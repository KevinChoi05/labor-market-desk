#!/usr/bin/env python3
"""Inline data/bls.json into src/template.html and write index.html."""
import os
from datetime import date

root = os.path.join(os.path.dirname(__file__), "..")
tpl = open(os.path.join(root, "src", "template.html")).read()
data = open(os.path.join(root, "data", "bls.json")).read()
html = tpl.replace("/*DATA*/", data)
today = date.today()
html = html.replace('const RETRIEVED = "November 16, 2026";',
                    f'const RETRIEVED = "{today:%B} {today.day}, {today.year}";')
open(os.path.join(root, "index.html"), "w").write(html)
print("Built index.html")
