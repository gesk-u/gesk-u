"""
Contribution grid, lilac palette, no cat.

The graph sits fully lit at rest, and a brightness wave sweeps left to right
across it every few seconds. Discrete steps rather than a smooth fade keep it
reading as pixel art, and because the resting state IS the finished graph, it
still looks right anywhere the animation does not run.

Everything is authored in ART PIXELS and wrapped in one scale(), so every edge
lands on a pixel boundary.

Data: it fetches your real contribution calendar from GitHub's GraphQL API when
GH_TOKEN and GH_LOGIN are set in the environment, and falls back to generated
sample data when they are not, so it still runs locally with no setup.

    GH_LOGIN=gesk-u GH_TOKEN=ghp_xxx python contrib_grid.py

GH_TOKEN must be a classic personal access token with the read:user scope. The
contribution calendar is not available without one. Keep it in Actions secrets,
never in the repo.

Knobs: PX (size), CELL/GAP (tile geometry), FACE/EDGE (the colour scale),
RIPPLE (how fast the wave crosses), T (seconds between sweeps).

Run:  python contrib_grid.py   ->  contrib-grid.svg
"""
import json, os, random, pathlib, urllib.request

random.seed(17)

PX = 2                      # svg units per art pixel
ROWS = 7
CELL, GAP = 5, 1
PITCH = CELL + GAP
GH = ROWS * PITCH - GAP
ML, MT, MB = 7, 10, 15
AH = MT + GH + MB

LEAD = 0.6                  # quiet before the wave starts
RIPPLE = 0.034              # seconds of delay per column
STEPGAP = 0.10              # between brightness steps
T = 9.0                     # seconds between sweeps

BG = "#0d0d14"
EMPTY = "#1b1b25"
EMPTY_EDGE = "#14141c"
FACE = ["#1b1b25", "#43356b", "#6450ad", "#9279e6", "#c8afff"]
EDGE = ["#14141c", "#2d2449", "#443878", "#6a54ad", "#947fd6"]
DIM = "#6e6a86"
PINK = "#ff4d9d"


def fake():
    """sample data, used when no token is present"""
    cols = 53
    g = [[0] * ROWS for _ in range(cols)]
    for c in range(cols):
        busy = 0.3 + 0.45 * (c / cols) + random.uniform(-0.1, 0.1)
        for r in range(ROWS):
            if random.random() < busy * (0.5 if r in (0, 6) else 1.0):
                g[c][r] = random.choices([1, 2, 3, 4], weights=[5, 4, 3, 2])[0]
    return g


QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { contributionCount weekday } }
      }
    }
  }
}
"""


def fetch(login, token):
    """real contribution calendar, counts bucketed into levels 0-4"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "contrib-grid"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "graphql error"))
    weeks = payload["data"]["user"]["contributionsCollection"] \
                   ["contributionCalendar"]["weeks"]

    counts = sorted(d["contributionCount"] for w in weeks
                    for d in w["contributionDays"] if d["contributionCount"] > 0)
    if counts:
        # quartiles of your active days, the way GitHub shades its own graph
        cuts = [counts[int(len(counts) * f)] for f in (0.25, 0.50, 0.75)]
    else:
        cuts = [1, 2, 3]

    def level(n):
        if n <= 0:
            return 0
        return 1 + sum(n > c for c in cuts)

    g = [[0] * ROWS for _ in weeks]
    for c, week in enumerate(weeks):
        for d in week["contributionDays"]:
            g[c][d["weekday"]] = level(d["contributionCount"])
    return g


LOGIN, TOKEN = os.environ.get("GH_LOGIN"), os.environ.get("GH_TOKEN")
if LOGIN and TOKEN:
    grid = fetch(LOGIN, TOKEN)
    print(f"fetched {LOGIN}: {len(grid)} weeks")
else:
    grid = fake()
    print("no GH_LOGIN/GH_TOKEN set - using sample data")

COLS = len(grid)
GW = COLS * PITCH - GAP
AW = GW + ML * 2
total = sum(1 for c in range(COLS) for r in range(ROWS) if grid[c][r])

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {AW * PX} {AH * PX}" '
       f'width="{AW * PX}" height="{AH * PX}" shape-rendering="crispEdges" role="img" '
       f'aria-label="A year of contributions">',
       f'<rect width="{AW * PX}" height="{AH * PX}" fill="{BG}"/>',
       f'<g transform="scale({PX})">']

for c in range(COLS):
    up = LEAD + c * RIPPLE
    for r in range(ROWS):
        x, y = ML + c * PITCH, MT + r * PITCH
        lvl = grid[c][r]
        if not lvl:
            svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                       f'fill="{EMPTY_EDGE}"/>'
                       f'<rect x="{x}" y="{y}" width="{CELL - 1}" height="{CELL - 1}" '
                       f'fill="{EMPTY}"/>')
            continue

        # at rest the tile shows its real colour; the wave lifts it two steps
        # brighter and drops it back
        up1, up2 = min(4, lvl + 1), min(4, lvl + 2)
        kt = ["0"] + [f"{(up + n * STEPGAP) / T:.5f}" for n in range(4)] + ["1"]
        face_vals = [FACE[lvl], FACE[up1], FACE[up2], FACE[up1], FACE[lvl], FACE[lvl]]
        edge_vals = [EDGE[lvl], EDGE[up1], EDGE[up2], EDGE[up1], EDGE[lvl], EDGE[lvl]]
        anim = (lambda vals: f'<animate attributeName="fill" dur="{T}s" '
                             f'repeatCount="indefinite" calcMode="discrete" '
                             f'keyTimes="{";".join(kt)}" values="{";".join(vals)}"/>')
        svg.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{EDGE[lvl]}">'
            f'{anim(edge_vals)}</rect>'
            f'<rect x="{x}" y="{y}" width="{CELL - 1}" height="{CELL - 1}" fill="{FACE[lvl]}">'
            f'{anim(face_vals)}</rect>')

svg.append(
    f'<text x="{ML}" y="{AH - 5}" fill="{DIM}" font-size="6" letter-spacing="1" '
    f'font-family="ui-monospace, \'Courier New\', monospace">gesk-u</text>'
    f'<text x="{AW - ML}" y="{AH - 5}" fill="{PINK}" font-size="6" text-anchor="end" '
    f'letter-spacing="1" font-family="ui-monospace, \'Courier New\', monospace">'
    f'{total} active days</text>')
svg.append('</g></svg>')

out = "".join(svg)
pathlib.Path(os.environ.get('OUT', 'contrib-grid.svg')).write_text(out)
print(f"{AW * PX}x{AH * PX}, loop {T}s, {total} active days, {len(out) // 1024} KB")
