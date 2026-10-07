import json, os, re, time, urllib.request, datetime

KEY = os.environ["API_KEY"]
BASE = "https://v3.football.api-sports.io/"
today = datetime.datetime.now(datetime.timezone.utc).date()
now = datetime.datetime.now(datetime.timezone.utc)
LAST_ERR = {}

def call(path):
    global LAST_ERR
    req = urllib.request.Request(BASE + path, headers={"x-apisports-key": KEY})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    LAST_ERR = data.get("errors") or {}
    if LAST_ERR:
        print("API errors:", LAST_ERR)
    return data.get("response", [])

def plan_blocked():
    return isinstance(LAST_ERR, dict) and "plan" in LAST_ERR

LIVE = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE"}
DONE = {"FT", "AET", "PEN"}
SKIP = re.compile(r"\bu-?\d{2}\b|women|\(w\)|reserve|youth|development league", re.I)
TOP = re.compile(
    r"champions league|europa|conference league|nations league|euro championship|world cup|asian cup|"
    r"cup of nations|copa america|arab|gulf cup|premier league - england|la liga|serie a - italy|"
    r"bundesliga - germany|ligue 1 - france|saudi|egypt|qatar|united-arab|morocco|algeria|tunisia|"
    r"kuwait|iraq|jordan", re.I)

# ---------- المباريات (3 طلبات) ----------
out = []
seen = {}
for delta in (-1, 0, 1):
    day = (today + datetime.timedelta(days=delta)).isoformat()
    for f in call(f"fixtures?date={day}"):
        fx, lg, tm, sc = f["fixture"], f["league"], f["teams"], f.get("score", {})
        ht = sc.get("halftime") or {}
        seen[lg["id"]] = (lg["name"], lg["country"], lg["season"])
        out.append({
