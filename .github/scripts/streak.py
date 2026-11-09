"""Build dist/streak.svg from the GitHub contribution calendar. Stdlib only."""
import datetime as dt
import json
import os
import sys
import urllib.request

USER = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "dist/streak.svg"
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){createdAt
contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""


def gql(variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "profile-streak"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


now = dt.datetime.now(dt.timezone.utc)
first = gql({"login": USER, "from": (now - dt.timedelta(days=364)).isoformat(), "to": now.isoformat()})
created = dt.datetime.fromisoformat(first["createdAt"].replace("Z", "+00:00"))

days = {}
end = now
while end > created:
    start = max(created, end - dt.timedelta(days=364))
    user = gql({"login": USER, "from": start.isoformat(), "to": end.isoformat()})
    for w in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in w["contributionDays"]:
            days[d["date"]] = d["contributionCount"]
    end = start - dt.timedelta(seconds=1)

dates = sorted(days)
total = sum(days.values())
first_day = next((d for d in dates if days[d] > 0), dates[0])

# longest streak
best, best_range, run, run_start = 0, (None, None), 0, None
for d in dates:
    if days[d] > 0:
        run_start = d if run == 0 else run_start
        run += 1
        if run > best:
            best, best_range = run, (run_start, d)
    else:
        run = 0

# current streak (today with no commits yet doesn't break it)
i = len(dates) - 1
if days[dates[i]] == 0:
    i -= 1
cur, cur_end = 0, dates[i] if i >= 0 else None
while i >= 0 and days[dates[i]] > 0:
    cur += 1
    i -= 1
cur_start = dates[i + 1] if cur else None


def fmt(d, year=False):
    x = dt.date.fromisoformat(d)
    s = x.strftime("%b ") + str(x.day)
    return s + (f", {x.year}" if year or x.year != now.year else "")


def rng(a, b):
    return f"{fmt(a)} - {fmt(b)}" if a else "no streak yet"


svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195">
<style>
.n{{font:700 28px 'Segoe UI',Ubuntu,sans-serif;fill:#fff}}
.l{{font:400 14px 'Segoe UI',Ubuntu,sans-serif;fill:#ffb000}}
.d{{font:400 12px 'Segoe UI',Ubuntu,sans-serif;fill:#8b8b8b}}
.f{{animation:in .6s ease backwards}}
.c{{animation:pop .9s ease backwards}}
.fl{{transform-origin:247.5px 19px;animation:flick 1.6s ease-in-out infinite}}
@keyframes in{{from{{opacity:0}}}}
@keyframes pop{{0%{{font-size:3px;opacity:.2}}80%{{font-size:34px;opacity:1}}}}
@keyframes flick{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.12,1.18)}}}}
</style>
<rect width="495" height="195" rx="6" fill="#0d0d0d"/>
<line x1="165" y1="28" x2="165" y2="170" stroke="#2a2a2a"/>
<line x1="330" y1="28" x2="330" y2="170" stroke="#2a2a2a"/>
<g text-anchor="middle">
  <g class="f" style="animation-delay:.2s">
    <text class="n" x="82.5" y="79">{total:,}</text>
    <text class="l" x="82.5" y="115">Total Contributions</text>
    <text class="d" x="82.5" y="146">{fmt(first_day, True)} - Present</text>
  </g>
  <circle cx="247.5" cy="71" r="40" fill="none" stroke="#ff4d00" stroke-width="5"/>
  <circle cx="247.5" cy="25" r="14" fill="#0d0d0d"/>
  <g class="fl"><path d="M247.5 4c3 7 10 10 10 19a10 10 0 0 1-20 0c0-5 3-8 4-11 1 4 3 5 5 5-2-5-1-9 1-13z" fill="#ff4d00"/></g>
  <text class="n c" x="247.5" y="81">{cur}</text>
  <g class="f" style="animation-delay:.4s">
    <text class="l" x="247.5" y="139" style="font-weight:700">Current Streak</text>
    <text class="d" x="247.5" y="160">{rng(cur_start, cur_end)}</text>
  </g>
  <g class="f" style="animation-delay:.6s">
    <text class="n" x="412.5" y="79">{best}</text>
    <text class="l" x="412.5" y="115">Longest Streak</text>
    <text class="d" x="412.5" y="146">{rng(*best_range)}</text>
  </g>
</g>
</svg>
"""
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    f.write(svg)
print(f"total={total} current={cur} longest={best}")
