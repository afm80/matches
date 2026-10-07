import json, os, urllib.request, datetime

KEY = os.environ["API_KEY"]
BASE = "https://v3.football.api-sports.io/"
now = datetime.datetime.now(datetime.timezone.utc)
today = now.date()
D = lambda n: (today + datetime.timedelta(days=n)).isoformat()
YESTERDAY, TODAY, TOMORROW = D(-1), D(0), D(1)

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
FINAL = {"FT", "AET", "PEN", "PST", "CANC", "ABD", "SUSP", "AWD", "WO"}

def fetch_day(day):
    """يرجع قائمة مباريات اليوم المطلوب، أو None إذا فشل الطلب (فلا نمسح القديم)."""
    try:
        req = urllib.request.Request(BASE + f"fixtures?date={day}", headers={"x-apisports-key": KEY})
        data = json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:
        print("request failed:", e)
        return None
    if data.get("errors"):
        print("API errors:", data["errors"])
        return None
    out = []
    for f in data.get("response", []):
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
    return out

# ---- البيانات السابقة ----
prev, daily = [], ""
if os.path.exists("data.json"):
    try:
        old = json.load(open("data.json", encoding="utf-8"))
        prev, daily = old.get("matches", []), old.get("daily", "")
    except Exception:
        pass

# ---- ما الذي نجلبه في هذا التشغيل؟ ----
days = [TODAY]                                   # اليوم: في كل تشغيل (طلب واحد)
daily_run = daily != TODAY                       # أمس وغداً: مرة واحدة في اليوم
# مباراة أمس لم تنتهِ بعد (تمتد بعد منتصف الليل): نعيد جلب أمس في الساعات الأولى من اليوم فقط
yesterday_open = now.hour < 4 and any(m["t"][:10] == YESTERDAY and m["s"] not in FINAL for m in prev)
if daily_run:
    days += [YESTERDAY, TOMORROW]
elif yesterday_open:
    days.append(YESTERDAY)

fresh, ok_days = [], []
for day in days:
    res = fetch_day(day)
    if res is not None:
        fresh += res
        ok_days.append(day)

# ---- الدمج: الجديد يستبدل أيامه، والباقي يبقى من السابق ----
window = {YESTERDAY, TODAY, TOMORROW}
kept = [m for m in prev if m["li"] in KEEP and m["t"][:10] in window and m["t"][:10] not in ok_days]
matches = sorted(kept + fresh, key=lambda m: m["t"])
new_daily = TODAY if (daily_run and all(d in ok_days for d in (YESTERDAY, TOMORROW))) else daily

# نكتب الملف فقط عند وجود تغيير (لتقليل عمليات الرفع)
if matches != prev or new_daily != daily:
    with open("data.json", "w", encoding="utf-8") as fp:
        json.dump({"updated": now.isoformat(), "daily": new_daily, "matches": matches}, fp, ensure_ascii=False)
    print("saved", len(matches), "matches; fetched days:", ok_days)
else:
    print("no changes; fetched days:", ok_days)
