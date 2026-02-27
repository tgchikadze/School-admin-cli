with open("web/templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("currentUser.fullname", "currentUser.full_name")
html = html.replace(".fullname", ".full_name")

with open("web/templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Fixed!")
