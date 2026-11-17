#!/usr/bin/env python3
"""Download the BLS series used by the dashboard into data/bls.json.

Uses the public BLS API v2 (no key needed; limited to 25 requests/day and
10 years per request). Set BLS_API_KEY to raise the limits.
"""
import json, os, urllib.request
from datetime import date

SERIES = [
    # Household survey (CPS)
    "LNS14000000", "LNS13000000", "LNS11300000", "LNS12300060", "LNS13008636",
    "LNS14027662", "LNS14027660", "LNS14024887",
    # Establishment survey (CES)
    "CES0000000001", "CES0500000003",
    "CES1000000001", "CES2000000001", "CES3000000001", "CES4200000001", "CES4300000001",
    "CES5000000001", "CES5500000001", "CES6000000001", "CES6054150001", "CES6562000001",
    "CES7000000001", "CES9000000001",
    # JOLTS
    "JTS000000000000000JOL", "JTS000000000000000HIR", "JTS000000000000000QUR", "JTS000000000000000LDL",
    # Prices
    "CUUR0000SA0",
]
START_YEAR = 2019
URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "bls.json")


def fetch(ids, start, end):
    body = {"seriesid": ids, "startyear": str(start), "endyear": str(end)}
    if os.environ.get("BLS_API_KEY"):
        body["registrationkey"] = os.environ["BLS_API_KEY"]
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    if d.get("status") != "REQUEST_SUCCEEDED":
        raise SystemExit(f"BLS API error: {d.get('message')}")
    return d["Results"]["series"]


def main():
    end = date.today().year
    out = {}
    for i in range(0, len(SERIES), 25):
        for s in fetch(SERIES[i:i + 25], START_YEAR, end):
            pts = []
            for p in s["data"]:
                if not p["period"].startswith("M") or p["period"] == "M13":
                    continue
                try:
                    v = float(p["value"])
                except ValueError:
                    v = None  # "-" means not published
                pts.append([f"{p['year']}-{p['period'][1:]}", v])
            out[s["seriesID"]] = sorted(pts)
    missing = set(SERIES) - set(out)
    if missing:
        raise SystemExit(f"Missing series: {sorted(missing)}")
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"Wrote {len(out)} series to data/bls.json")


if __name__ == "__main__":
    main()
