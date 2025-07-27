from flask_session import Session
from flask import Flask, redirect, url_for, session, request, render_template,abort
from authlib.integrations.flask_client import OAuth
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = "nomeacuerdo123"
Session(app)

def ip_permitida():
    ip = request.remote_addr

    if ip == "127.0.0.1":  # Acceso local permitido
        return True
    partes = ip.split(".")
    if len(partes) != 4:
        return False
    if partes[0] == "10" and partes[1] == "66":
        try:
            x1 = int (partes[2])
            x2 = int (partes[3])
            return 100 <= x1 <= 300 and 100 <= x2 <= 300
        except ValueError:
            return False
    return False
# --------------------------
# Login con Google (OAuth)
# --------------------------
with open('client_secret.json') as f:
    client_info = json.load(f)['web']

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=client_info['client_id'],
    client_secret=client_info['client_secret'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


'''Acceso a Google Sheets'''
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Fichada").sheet1

filas = sheet.get_all_values()

fecha_limite = datetime.now() - timedelta(days=60)

nuevas_filas =[filas[0]]

for fila in filas[1:]:
    try: 
        fecha_str=fila[2]
        fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
        if fecha >= fecha_limite:
            nuevas_filas.append(fila)

    except:
        pass

sheet.clear()
sheet.append_rows(nuevas_filas)

@app.route("/")
def index():
    if not ip_permitida():
        abort(403)
    if "email" in session:
        return render_template("home.html", email=session["email"])
    return render_template("index.html")

@app.route("/login")
def login():
    if not ip_permitida():
        abort(403)
    return google.authorize_redirect(redirect_uri="http://127.0.0.1:5000/auth/callback")

@app.route("/auth/callback")
def callback():
    if not ip_permitida():
        abort(403)
    token = google.authorize_access_token()
    userinfo = google.get('https://openidconnect.googleapis.com/v1/userinfo').json()
    session["email"] = userinfo["email"]
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/fichar/<accion>")
def fichar(accion):
    if not ip_permitida():
        abort(403)
    if "email" not in session:
        return redirect(url_for("index"))
    
    email = session["email"]
    fecha = datetime.now().strftime("%d/%m/%Y")
    hora = datetime.now().strftime("%H:%M:%S")
    ip = request.remote_addr
    ubicacion = "Parque Patricios" if ip.startswith("10.66") else ip

    if accion not in ["Ingreso", "Salida"]:
        return "Acción no válida."

    # Guardar en Google Sheets
    sheet.append_row([email, accion, fecha, hora, ubicacion])

    return render_template(
        "fichada_resultado.html",
        accion=accion.capitalize(),
        email=email,
        ubicacion=ubicacion,
        hora=hora,
        fecha=fecha
    )
@app.route("/historial", methods=["GET", "POST"])
def historial():
    if not ip_permitida():
        abort(403)
    if "email" not in session:
        return redirect(url_for("index"))

    email = session["email"]
    registros = sheet.get_all_records()
    es_admin = email == "vicente.sosa@ctl.com.ar","julian.cordoba@ctl.com.ar"
    correos_unicos = sorted(set(r['Nombre'] for r in registros))

    filtro = ""
    desde = ""
    hasta = ""

    if request.method == "POST":
        filtro = request.form.get("email", "")
        desde = request.form.get("desde", "")
        hasta = request.form.get("hasta", "")

        if filtro:
            registros = [r for r in registros if r['Nombre'] == filtro]

        if desde:
            registros = [r for r in registros if r['Fecha'] >= datetime.strptime(desde, "%Y-%m-%d").strftime("%d/%m/%Y")]
        if hasta:
            registros = [r for r in registros if r['Fecha'] <= datetime.strptime(hasta, "%Y-%m-%d").strftime("%d/%m/%Y")]
    else:
        if not es_admin:
            registros = [r for r in registros if r['Nombre'] == email]

    return render_template(
        "historial.html",
        registros=registros,
        es_admin=es_admin,
        emails=correos_unicos,
        filtro=filtro,
        desde=desde,
        hasta=hasta,
        email=email
    )

if __name__ == "__main__":
    app.run(debug=True)
