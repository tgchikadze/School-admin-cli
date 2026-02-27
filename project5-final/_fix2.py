with open("web/templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Replace hardcoded user-block with dynamic one
old = """        <span class="material-icons" style="font-size:16px; vertical-align:middle">person</span>
        admin \xb7 \u0417\u0430\u0432\u0443\u0447"""

new = """        <span class="material-icons" style="font-size:16px; vertical-align:middle">person</span>
        <span id="ub-name">...</span>"""

html = html.replace(old, new)

# Add user-block update + logout into DOMContentLoaded
init_code = """
  try {
    var me = await api('/api/me');
    var ub = document.getElementById('ub-name');
    if (ub && me) ub.innerHTML = (me.full_name || me.username) + ' &middot; ' + me.role +
      '<br><a href="#" onclick="doLogout()" style="color:#ef5350;font-size:0.75rem">Выйти</a>';
  } catch(e) { window.location.href = '/login'; }
"""

# Insert before "console.log('Biotech225 Admin init...')"
html = html.replace(
    "console.log('Biotech225 Admin init...');",
    "console.log('Biotech225 Admin init...');" + init_code
)

# Add doLogout function before closing </script>
if "doLogout" not in html:
    html = html.replace(
        "</script>\n</body>",
        "async function doLogout(){await fetch('/api/logout',{method:'POST'});window.location.href='/login';}\n</script>\n</body>"
    )

with open("web/templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Fixed! user-block + logout added")
