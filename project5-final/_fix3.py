with open("web/templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

logout_fn = "\nasync function doLogout(){await fetch('/api/logout',{method:'POST'});window.location.href='/login';}\n"

if "doLogout" not in html:
    # Insert before the LAST </script> in the file
    pos = html.rfind("</script>")
    if pos > 0:
        html = html[:pos] + logout_fn + html[pos:]
        print("doLogout inserted!")
    else:
        print("ERROR: no </script> found")
else:
    print("doLogout already exists")

with open("web/templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)
