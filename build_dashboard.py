import json, os

BASE = r"D:\basketball_odds"
tpl = open(os.path.join(BASE, "dashboard_template.html"), encoding="utf-8").read()
chart = open(os.path.join(BASE, "chart.umd.min.js"), encoding="utf-8").read()
data = open(os.path.join(BASE, "dashboard_data.json"), encoding="utf-8").read()

html = tpl.replace("/*__CHARTJS__*/", chart)
html = html.replace("/*__DATA__*/", data.replace("</", "<\\/"))
out = os.path.join(BASE, "dashboard.html")
open(out, "w", encoding="utf-8").write(html)
print("dashboard:", out, round(os.path.getsize(out) / 1048576, 2), "MB")
