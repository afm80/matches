import json, os, re, time, urllib.request, datetime

KEY = os.environ["API_KEY"]
BASE = "https://v3.football.api-sports.io/"
today = datetime.datetime.now(datetime.timezone.utc).date()

def call(path):
    req = urllib.request.Request(BASE + path, headers={"x-apisports-key": KEY})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if data.get("errors"):
        print("API errors:", data["errors"])
    return data.get("response", [])

LIVE = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE"}
DONE = {"FT", "AET", "PEN"}
SKIP = re.compile(r"\bu-?\d{2}\b|women|\(w\)|reserve|youth|development league", re.I)
TOP = re.compile(
    r"champions league|europa|conference league|nations league|euro championship|world cup|asian cup|"
    r"cup of nations|copa america|arab|gulf cup|premier league - england|la liga|serie a - italy|"
    r"bundesliga - germany|ligue 1 - france|saudi|egypt|qatar|united-arab|morocco|algeria|tunisia|"
    r"kuwait|iraq|jordan", re.I)

out = []
seen = {}
for delta in (-1, 0, 1):
    day = (today + datetime.timedelta(days=delta)).isoformat()
    for f in call(f"fixtures?date={day}"):
        fx, lg, tm, sc = f["fixture"], f["league"], f["teams"], f.get("score", {})
        ht = sc.get("halftime") or {}
        seen[lg["id"]] = (lg["name"], lg["country"], lg["season"])
        out.append({
            "id": fx["id"],
            "li": lg["id"], "se": lg["season"],
            "t": fx["date"],
            "s": fx["status"]["short"],
            "el": fx["status"].get("elapsed"),
            "lg": f'{lg["name"]} - {lg["country"]}',
            "rd": lg.get("round"),
            "v": (fx.get("venue") or {}).get("name"),
            "c": (fx.get("venue") or {}).get("city"),
            "r": fx.get("referee"),
            "h": tm["home"]["name"], "hl": tm["home"]["logo"], "hid": tm["home"]["id"],
            "a": tm["away"]["name"], "al": tm["away"]["logo"],
            "gh": f["goals"]["home"], "ga": f["goals"]["away"],
            "hth": ht.get("home"), "hta": ht.get("away"),
        })
    time.sleep(7)

out.sort(key=lambda m: m["t"])

# أحداث المباريات (أهداف وبطاقات) للبطولات المهمة فقط، حتى 40 مباراة لتوفير الطلبات
want = [m for m in out
        if (m["s"] in LIVE or m["s"] in DONE)
        and TOP.search(m["lg"]) and not SKIP.search(f'{m["lg"]} {m["h"]} {m["a"]}')]
want = want[-40:]
by_id = {m["id"]: m for m in out}
for i in range(0, len(want), 20):
    ids = "-".join(str(m["id"]) for m in want[i:i + 20])
    for f in call(f"fixtures?ids={ids}"):
        m = by_id.get(f["fixture"]["id"])
        if not m:
            continue
        evs = []
        for e in f.get("events") or []:
            kind = None
            if e["type"] == "Goal":
                kind = {"Own Goal": "og", "Penalty": "pg"}.get(e["detail"], "g" if e["detail"] != "Missed Penalty" else None)
            elif e["type"] == "Card":
                kind = "y" if e["detail"] == "Yellow Card" else "r"
            if not kind:
                continue
            el = e["time"]["elapsed"]
            if e["time"].get("extra"):
                el = f'{el}+{e["time"]["extra"]}'
            side = "h" if e["team"]["id"] == m["hid"] else "a"
            evs.append([str(el), side, e["player"]["name"] or "", kind])
        m["e"] = evs
    time.sleep(7)


# ---------- الترتيب والهدافون للبطولات المهمة (مرة كل 20 ساعة تقريباً لكل بطولة) ----------
PRI = [re.compile(x, re.I) for x in [
    r"^uefa champions league -", r"^uefa europa league -", r"^uefa (europa )?conference league -",
    r"^uefa nations league -", r"euro championship|uefa euro", r"^world cup", r"asian cup",
    r"^afc champions league", r"^africa cup of nations|^cup of nations", r"^caf champions league",
    r"^caf confederation cup", r"^copa america", r"arab cup|arab club champions", r"gulf cup",
    r"^premier league - england", r"^la liga - spain", r"^serie a - italy", r"^bundesliga - germany",
    r"^ligue 1 - france", r"saudi", r"- egypt$",
    r"- (qatar|united-arab-emirates|uae|kuwait|iraq|jordan|morocco|algeria|tunisia|bahrain|oman|lebanon|libya|sudan|syria|palestine|yemen)$"]]
EXCL = re.compile(r"first division|second|third|division [23]|league 2|amateur|friendl|qualification|play-?off", re.I)

def rank_of(name):
    if EXCL.search(name) or SKIP.search(name):
        return None
    for i, rx in enumerate(PRI):
        if rx.search(name):
            return i
    return None

cur = today.year if today.month >= 7 else today.year - 1
SEEDS = {39: ("Premier League", "England"), 140: ("La Liga", "Spain"), 135: ("Serie A", "Italy"),
         78: ("Bundesliga", "Germany"), 61: ("Ligue 1", "France"), 2: ("UEFA Champions League", "World"),
         3: ("UEFA Europa League", "World"), 848: ("UEFA Europa Conference League", "World"),
         307: ("Pro League", "Saudi-Arabia"), 233: ("Premier League", "Egypt")}

tracked = {}
for lid, (n, c) in SEEDS.items():
    tracked[lid] = {"id": lid, "name": n, "country": c, "season": cur, "rank": rank_of(f"{n} - {c}") or 0}
for lid, (n, c, se) in seen.items():
    r = rank_of(f"{n} - {c}")
    if r is None:
        continue
    if lid in tracked:
        tracked[lid]["season"] = se
        tracked[lid]["name"], tracked[lid]["country"] = n, c
    else:
        tracked[lid] = {"id": lid, "name": n, "country": c, "season": se, "rank": r}
order = sorted(tracked.values(), key=lambda x: (x["rank"], x["id"]))[:20]

old = {}
if os.path.exists("standings.json"):
    try:
        old = json.load(open("standings.json", encoding="utf-8")).get("leagues", {})
    except Exception:
        old = {}

now = datetime.datetime.now(datetime.timezone.utc)
def fresh(e):
    try:
        return (now - datetime.datetime.fromisoformat(e["updated"])).total_seconds() < 20 * 3600
    except Exception:
        return False

budget = 12
result = {}
for t in order:
    prev = old.get(str(t["id"]))
    entry = {"id": t["id"], "name": t["name"], "country": t["country"], "season": t["season"],
             "updated": "", "table": [], "scorers": []}
    if prev and prev.get("season") == t["season"]:
        entry.update({k: prev.get(k, entry[k]) for k in ("updated", "table", "scorers")})
    if not (prev and fresh(prev) and prev.get("season") == t["season"]) and budget >= 2:
        budget -= 2
        table = []
        for resp in call(f'standings?league={t["id"]}&season={t["season"]}'):
            for grp in resp["league"].get("standings", []):
                rows = [{"r": x["rank"], "n": x["team"]["name"], "l": x["team"]["logo"],
                         "p": x["all"]["played"], "w": x["all"]["win"], "d": x["all"]["draw"], "ls": x["all"]["lose"],
                         "gf": x["all"]["goals"]["for"], "ga": x["all"]["goals"]["against"],
                         "pt": x["points"], "g": x.get("group")} for x in grp]
                if rows:
                    table.append(rows)
        time.sleep(7)
        scorers = []
        for x in call(f'players/topscorers?league={t["id"]}&season={t["season"]}')[:15]:
            st = (x.get("statistics") or [{}])[0]
            scorers.append({"n": x["player"]["name"], "t": (st.get("team") or {}).get("name", ""),
                            "l": (st.get("team") or {}).get("logo", ""),
                            "g": (st.get("goals") or {}).get("total"), "a": (st.get("goals") or {}).get("assists")})
        time.sleep(7)
        if table or scorers or not entry["table"]:
            entry["table"], entry["scorers"] = table or entry["table"], scorers or entry["scorers"]
        entry["updated"] = now.isoformat()
    result[str(t["id"])] = entry

with open("standings.json", "w", encoding="utf-8") as fp:
    json.dump({"leagues": result}, fp, ensure_ascii=False)

for m in out:
    m.pop("hid", None)

with open("data.json", "w", encoding="utf-8") as fp:
    json.dump({"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(), "matches": out}, fp, ensure_ascii=False)
print("saved", len(out), "matches;", len(want), "with events")
