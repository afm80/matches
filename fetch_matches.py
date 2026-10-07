import json, os, urllib.request, datetime

KEY = os.environ["API_KEY"]
BASE = "https://v3.football.api-sports.io/"
now = datetime.datetime.now(datetime.timezone.utc)
today = now.date()

# الدوريات والبطولات المسموحة فقط (أرقام API-Football)
KEEP = {
    2, 3, 848,              # دوري أبطال أوروبا، الدوري الأوروبي، دوري المؤتمر
    5,                      # دوري الأمم الأوروبية
    4, 1,                   # كأس أمم أوروبا، كأس العالم
    7, 17,                  # كأس آسيا، دوري أبطال آسيا
    6, 36,                  # كأس أمم أفريقيا + تصفياتها
    9, 25,                  # كوبا أمريكا، كأس الخليج
    32, 30, 29, 34,         # تصفيات كأس العالم: أوروبا، آسيا، أفريقيا، أمريكا الجنوبية
    39, 140, 135, 78, 61,   # الإنجليزي، الإسباني، الإيطالي، الألماني، الفرنسي
    542,                    # الدوري العراقي
}

def call(path):
    req = urllib.request.Request(BASE + path, headers={"x-apisports-key": KEY})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if data.get("errors"):
        print("API errors:", data["errors"])
    return data.get("response", [])

# 3 طلبات فقط في كل تشغيل (أمس واليوم وغداً بتوقيت UTC) لتغطية كل المناطق الزمنية
out = []
for delta in (-1, 0, 1):
    day = (today + datetime.timedelta(days=delta)).isoformat()
    for f in call(f"fixtures?date={day}"):
        fx, lg, tm = f["fixture"], f["league"], f["teams"]
        if lg["id"] not in KEEP:
            continue
        out.append({
            "id": fx["id"], "li": lg["id"],
            "t": fx["date"], "s": fx["status"]["short"],
            "lg": f'{lg["name"]} - {lg["country"]}',
            "h": tm["home"]["name"], "hl": tm["home"]["logo"],
            "a": tm["away"]["name"], "al": tm["away"]["logo"],
            "gh": f["goals"]["home"], "ga": f["goals"]["away"],
        })
out.sort(key=lambda m: m["t"])

with open("data.json", "w", encoding="utf-8") as fp:
    json.dump({"updated": now.isoformat(), "matches": out}, fp, ensure_ascii=False)
print("saved", len(out), "matches")
