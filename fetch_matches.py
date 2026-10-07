import json, os, urllib.request, datetime

KEY = os.environ["API_KEY"]
today = datetime.datetime.now(datetime.timezone.utc).date()
out = []

for delta in (-1, 0, 1):
    day = (today + datetime.timedelta(days=delta)).isoformat()
    req = urllib.request.Request(
        f"https://v3.football.api-sports.io/fixtures?date={day}",
        headers={"x-apisports-key": KEY},
    )
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if data.get("errors"):
        print("API errors:", data["errors"])
    for f in data.get("response", []):
        out.append({
            "t": f["fixture"]["date"],
            "s": f["fixture"]["status"]["short"],
            "lg": f'{f["league"]["name"]} - {f["league"]["country"]}',
            "h": f["teams"]["home"]["name"], "hl": f["teams"]["home"]["logo"],
            "a": f["teams"]["away"]["name"], "al": f["teams"]["away"]["logo"],
            "gh": f["goals"]["home"], "ga": f["goals"]["away"],
        })

out.sort(key=lambda m: m["t"])
with open("data.json", "w", encoding="utf-8") as fp:
    json.dump({"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(), "matches": out}, fp, ensure_ascii=False)
print("saved", len(out), "matches")
