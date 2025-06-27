from flask_session import Session
from flask import Flask, redirect, url_for, session, request, render_template
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
    client_kwargs={
        'scope': 'openid email profile'
    }
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
    if "email" in session:
        return render_template("home.html", email=session["email"])
    return render_template("index.html")

@app.route("/login")
def login():
    return google.authorize_redirect(redirect_uri="http://127.0.0.1:5000/auth/callback")

@app.route("/auth/callback")
def callback():
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

    return f"{accion} registrado para {email} a las {hora} desde {ip}"

if __name__ == "__main__":
    app.run(debug=True)
