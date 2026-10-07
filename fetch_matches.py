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
for delta in (-1, 0, 1):
    day = (today + datetime.timedelta(days=delta)).isoformat()
    for f in call(f"fixtures?date={day}"):
        fx, lg, tm, sc = f["fixture"], f["league"], f["teams"], f.get("score", {})
        ht = sc.get("halftime") or {}
        out.append({
            "id": fx["id"],
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

for m in out:
    m.pop("hid", None)

with open("data.json", "w", encoding="utf-8") as fp:
    json.dump({"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(), "matches": out}, fp, ensure_ascii=False)
print("saved", len(out), "matches;", len(want), "with events")
