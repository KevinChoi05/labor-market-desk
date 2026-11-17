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
# The template is page content only (claude.ai artifacts add the document
# skeleton themselves); wrap it so the file works as a standalone web page.
RESET = (":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);"
         "padding-bottom:env(safe-area-inset-bottom,0px)}"
         "body{margin:0;font:14px system-ui,-apple-system,Segoe UI,sans-serif}"
         "img{max-width:100%}[hidden]{display:none!important}")
html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f"<style>{RESET}</style></head><body>{html}</body></html>")
open(os.path.join(root, "index.html"), "w").write(html)
print("Built index.html")
