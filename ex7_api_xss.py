from flask import Flask, render_template_string

from common import get_mongo_db

app = Flask(__name__)

p1 = "<script>alert('xss1')</script>"
p2 = 'x" onerror="alert(\'xss2\')'

incidentes_exemplo = [
    {"titulo": p1, "ativo": "SRV-WEB01"},
    {"titulo": "Port scan", "ativo": p2},
]

TEMPLATE_SEGURO = """
<!DOCTYPE html>
<html>
<head><title>Dashboard (seguro)</title></head>
<body>
<h1>Incidentes</h1>
<table border="1">
  <tr><th>Título</th><th>Ativo</th></tr>
  {% for inc in incidentes %}
  <tr>
    <td>{{ inc.titulo }}</td>
    <td><img src="/icone.png" alt="{{ inc.ativo }}"></td>
  </tr>
  {% endfor %}
</table>
</body>
</html>
"""

# Versão insegura de propósito: concatenação manual, sem escape.
# NÃO faça isso — está aqui só para comparação lado a lado.
TEMPLATE_INSEGURO_HEADER = """
<!DOCTYPE html>
<html>
<head><title>Dashboard (INSEGURO - NÃO USE)</title></head>
<body>
<h1>Incidentes (versão insegura, só para comparação)</h1>
<table border="1">
  <tr><th>Título</th><th>Ativo</th></tr>
"""
TEMPLATE_INSEGURO_FOOTER = """
</table>
</body>
</html>
"""


def popular_mongo():
    db = get_mongo_db()
    col = db["incidentes_dashboard"]
    col.delete_many({})
    col.insert_many(incidentes_exemplo)
    return col


@app.after_request
def aplicar_headers_seguranca(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.route("/dashboard")
def dashboard():
    db = get_mongo_db()
    col = db["incidentes_dashboard"]
    incidentes = list(col.find({}, {"_id": 0}))
    # Jinja2 autoescapa {{ inc.titulo }} e {{ inc.ativo }} — o texto do
    # payload aparece literalmente na página, nunca é interpretado
    # como HTML/JS.
    return render_template_string(TEMPLATE_SEGURO, incidentes=incidentes)


@app.route("/dashboard-inseguro")
def dashboard_inseguro():
    db = get_mongo_db()
    col = db["incidentes_dashboard"]
    incidentes = list(col.find({}, {"_id": 0}))

    html = TEMPLATE_INSEGURO_HEADER
    for inc in incidentes:
        # concatenação direta = sem escape = XSS reproduzido de propósito
        html += f'<tr><td>{inc["titulo"]}</td><td><img src="/icone.png" alt="{inc["ativo"]}"></td></tr>'
    html += TEMPLATE_INSEGURO_FOOTER

    return html


if __name__ == "__main__":
    popular_mongo()
    app.run(debug=True, host="0.0.0.0", port=5007)
