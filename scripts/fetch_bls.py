#!/usr/bin/env python3
"""Download every BLS series the dashboard uses into data/*.json.

Uses the public BLS API v2. Without a key it allows 25 requests a day,
25 series per request and 10 years per request; this script makes about
13 requests. Set BLS_API_KEY to raise the limits (50 series, 20 years,
500 requests/day): https://data.bls.gov/registrationEngine/
"""
import json, os, sys, time, urllib.request
from datetime import date

URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
KEY = os.environ.get("BLS_API_KEY")
BATCH = 50 if KEY else 25

# National indicators (monthly)
NATIONAL = [
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

# States: FIPS code -> (postal, name)
STATES = {
    "01": ("AL", "Alabama"), "02": ("AK", "Alaska"), "04": ("AZ", "Arizona"), "05": ("AR", "Arkansas"),
    "06": ("CA", "California"), "08": ("CO", "Colorado"), "09": ("CT", "Connecticut"), "10": ("DE", "Delaware"),
    "11": ("DC", "District of Columbia"), "12": ("FL", "Florida"), "13": ("GA", "Georgia"), "15": ("HI", "Hawaii"),
    "16": ("ID", "Idaho"), "17": ("IL", "Illinois"), "18": ("IN", "Indiana"), "19": ("IA", "Iowa"),
    "20": ("KS", "Kansas"), "21": ("KY", "Kentucky"), "22": ("LA", "Louisiana"), "23": ("ME", "Maine"),
    "24": ("MD", "Maryland"), "25": ("MA", "Massachusetts"), "26": ("MI", "Michigan"), "27": ("MN", "Minnesota"),
    "28": ("MS", "Mississippi"), "29": ("MO", "Missouri"), "30": ("MT", "Montana"), "31": ("NE", "Nebraska"),
    "32": ("NV", "Nevada"), "33": ("NH", "New Hampshire"), "34": ("NJ", "New Jersey"), "35": ("NM", "New Mexico"),
    "36": ("NY", "New York"), "37": ("NC", "North Carolina"), "38": ("ND", "North Dakota"), "39": ("OH", "Ohio"),
    "40": ("OK", "Oklahoma"), "41": ("OR", "Oregon"), "42": ("PA", "Pennsylvania"), "44": ("RI", "Rhode Island"),
    "45": ("SC", "South Carolina"), "46": ("SD", "South Dakota"), "47": ("TN", "Tennessee"), "48": ("TX", "Texas"),
    "49": ("UT", "Utah"), "50": ("VT", "Vermont"), "51": ("VA", "Virginia"), "53": ("WA", "Washington"),
    "54": ("WV", "West Virginia"), "55": ("WI", "Wisconsin"), "56": ("WY", "Wyoming"),
}
STATE_UR = "LASST{}0000000000003"      # LAUS unemployment rate, seasonally adjusted
STATE_JOBS = "SMS{}000000000000001"    # CES state total nonfarm, seasonally adjusted (thousands)

# Occupations (OEWS, national, all industries): SOC code -> (name, group)
OCCUPATIONS = {
    "000000": ("All occupations", "All"),
    "111021": ("General and operations managers", "Business"),
    "113021": ("Computer and information systems managers", "Tech"),
    "131111": ("Management analysts", "Business"),
    "131161": ("Market research analysts", "Business"),
    "132011": ("Accountants and auditors", "Business"),
    "132051": ("Financial and investment analysts", "Business"),
    "151211": ("Computer systems analysts", "Tech"),
    "151212": ("Information security analysts", "Tech"),
    "151252": ("Software developers", "Tech"),
    "152051": ("Data scientists", "Tech"),
    "231011": ("Lawyers", "Professional"),
    "252021": ("Elementary school teachers", "Education"),
    "271024": ("Graphic designers", "Professional"),
    "291051": ("Pharmacists", "Health care"),
    "291141": ("Registered nurses", "Health care"),
    "291171": ("Nurse practitioners", "Health care"),
    "311131": ("Nursing assistants", "Health care"),
    "352014": ("Cooks, restaurant", "Service"),
    "353023": ("Fast food and counter workers", "Service"),
    "353031": ("Waiters and waitresses", "Service"),
    "412011": ("Cashiers", "Sales"),
    "412031": ("Retail salespersons", "Sales"),
    "434051": ("Customer service representatives", "Office"),
    "436014": ("Secretaries and administrative assistants", "Office"),
    "472061": ("Construction laborers", "Trades"),
    "472111": ("Electricians", "Trades"),
    "472152": ("Plumbers, pipefitters, and steamfitters", "Trades"),
    "499021": ("HVAC mechanics and installers", "Trades"),
    "533032": ("Heavy and tractor-trailer truck drivers", "Transportation"),
    "537062": ("Laborers and freight, stock, and material movers", "Transportation"),
}
# OEWS datatypes: 01 employment, 13 annual median wage, 11 annual 10th pct, 15 annual 90th pct
OCC_TYPES = {"01": "emp", "13": "median", "11": "p10", "15": "p90"}


def post(ids, start, end):
    body = {"seriesid": ids, "startyear": str(start), "endyear": str(end)}
    if KEY:
        body["registrationkey"] = KEY
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.load(r)
            break
        except OSError as e:
            if attempt == 2:
                raise
            print(f"  retrying after error: {e}", file=sys.stderr)
            time.sleep(5)
    if d.get("status") != "REQUEST_SUCCEEDED":
        raise SystemExit(f"BLS API error: {d.get('message')}")
    return d["Results"]["series"]


def num(v):
    try:
        return float(v)
    except ValueError:
        return None  # "-" = not published, "#" / "*" = top-coded or suppressed


def monthly(ids, start, end):
    out = {}
    for i in range(0, len(ids), BATCH):
        for s in post(ids[i:i + BATCH], start, end):
            pts = [[f"{p['year']}-{p['period'][1:]}", num(p["value"])]
                   for p in s["data"] if p["period"].startswith("M") and p["period"] != "M13"]
            if pts:
                out[s["seriesID"]] = sorted(pts)
    missing = [x for x in ids if x not in out]
    if missing:
        raise SystemExit(f"No data returned for: {missing}")
    return out


def save(name, obj):
    with open(os.path.join(DATA, name), "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    print(f"Wrote data/{name}")


def main():
    end = date.today().year
    start = max(2019, end - (19 if KEY else 9))

    save("bls.json", monthly(NATIONAL, start, end))

    ur = monthly([STATE_UR.format(f) for f in STATES], start, end)
    jobs = monthly([STATE_JOBS.format(f) for f in STATES], start, end)
    save("states.json", {
        code: {"name": name, "fips": f, "ur": ur[STATE_UR.format(f)], "jobs": jobs[STATE_JOBS.format(f)]}
        for f, (code, name) in STATES.items()
    })

    ids = [f"OEUN0000000000000{soc}{t}" for soc in OCCUPATIONS for t in OCC_TYPES]
    occ, year = {}, None
    for i in range(0, len(ids), BATCH):
        for s in post(ids[i:i + BATCH], end - 2, end):
            if not s["data"]:
                continue
            p = s["data"][0]  # OEWS API serves only the latest annual estimate
            soc, t = s["seriesID"][17:23], s["seriesID"][23:]
            occ.setdefault(soc, {})[OCC_TYPES[t]] = num(p["value"])
            year = max(year or p["year"], p["year"])
    rows = []
    for soc, (name, group) in OCCUPATIONS.items():
        v = occ.get(soc, {})
        if v.get("emp") is None:
            print(f"  skipping {soc} {name}: no OEWS data", file=sys.stderr)
            continue
        rows.append({"soc": f"{soc[:2]}-{soc[2:]}", "name": name, "group": group, **v})
    save("occupations.json", {"year": year, "period": f"May {year}", "rows": rows})


if __name__ == "__main__":
    main()
