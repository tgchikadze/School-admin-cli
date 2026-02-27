with open("web/templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

fn = "async function doLogout(){await fetch('/api/logout',{method:'POST'});window.location.href='/login';}"

if "function doLogout" not in html:
    pos = html.rfind("</script>")
    html = html[:pos] + "\n" + fn + "\n" + html[pos:]
    print("doLogout function added at position", pos)
else:
    print("Already exists")

with open("web/templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)
