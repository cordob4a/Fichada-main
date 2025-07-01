from flask_session import Session
from flask import Flask, redirect, url_for, session, request, render_template,abort
from authlib.integrations.flask_client import OAuth
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = "nomeacuerdo123"
Session(app)

def ip_permitida():
    ip = request.remote_addr
    print(f"IP detectada: {ip}")  # <- Agregado para debug
    if ip == "127.0.0.1":  # Acceso local permitido
        return True
    if ip.startswith("10.66.118."):
        try:
            ultimo = int(ip.split(".")[3])
            return 1 <= ultimo <= 200
        except:
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

# --------------------------
# Rutas
# --------------------------
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

    if accion not in ["Ingreso", "Salida"]:
        return "Acción no válida."

    # Guardar en Google Sheets
    sheet.append_row([email, accion, fecha, hora, ip])

    return render_template(
        "fichada_resultado.html",
        accion=accion.capitalize(),
        email=email,
        ip=ip,
        hora=hora,
        fecha=fecha
    )

if __name__ == "__main__":
    app.run(debug=True)
