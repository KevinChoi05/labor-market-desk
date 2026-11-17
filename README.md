# Labor Market Desk

A single-page dashboard of the U.S. job market built from official
U.S. Bureau of Labor Statistics data, with an "Ask the data" chatbot that
answers questions using only those numbers.

- **Headline indicators:** unemployment rate, 3-month average payroll gains,
  job openings per unemployed person, quits rate, real wage growth.
- **Trend explorer:** unemployment, monthly job growth, openings vs. job seekers,
  hires and quits, wages vs. prices, unemployment by education and age,
  long-term unemployment.
- **Industries:** 12 sectors ranked by 12-month job growth, compared with Feb 2020.
- **States:** tile map of unemployment or 12-month job growth for all 50 states + DC;
  click a state to compare it with the U.S.
- **Jobs and pay:** employment and pay range for 30 common occupations.
- **Chatbot:** answers only from the page's data, with a `get_series` tool so
  answers cite real months and series IDs. On claude.ai it uses the artifact's
  built-in Claude access; on the public site it goes through `worker/`, a
  Cloudflare Worker that calls OpenRouter (Claude Haiku 5.5) with the key kept
  server-side, an origin check, per-IP rate limit and token cap.

## Data

Series from the BLS Public Data API v2: Current Population Survey (`LNS…`),
Current Employment Statistics (`CES…`, state `SMS…`), Local Area Unemployment
Statistics (`LASST…`), JOLTS (`JTS…`), CPI-U (`CUUR0000SA0`) and Occupational
Employment and Wage Statistics (`OEUN…`, latest May estimate only).
The full list is in `scripts/fetch_bls.py`. October 2025 household-survey and
CPI values were not published (federal shutdown); year-over-year math fills
that single month by averaging its neighbors.

## Layout

```
src/template.html     page source (HTML, CSS, JS); data goes in at /*DATA*/
data/bls.json         national series: {seriesId: [[YYYY-MM, value], ...]}
data/states.json      state unemployment rate and payrolls
data/occupations.json OEWS employment and pay by occupation
scripts/fetch_bls.py  re-download data from the BLS API
scripts/build.py      inline the data into index.html
index.html            built page (open directly in a browser)
junction.json         Junction project config
```

## Update the data

A GitHub Action (`.github/workflows/refresh-data.yml`) runs every Saturday,
pulls the latest BLS data and commits it when anything changed. Run it by hand
from the Actions tab. Add a free `BLS_API_KEY` repo secret for higher API limits.

To update locally:

```sh
python3 scripts/fetch_bls.py   # optional: export BLS_API_KEY=... for higher limits
python3 scripts/build.py
```

Then open `index.html`, or republish it as a claude.ai artifact.

## Chat backend (worker/)

```sh
cd worker
npx wrangler login
npx wrangler secret put OPENROUTER_API_KEY   # set a credit limit on this key in OpenRouter
npx wrangler deploy
```

Put the deployed URL in `worker/chat_url.txt` and rebuild. Change the model in
`worker/wrangler.toml` (`MODEL`). Logs: `npx wrangler tail`.
