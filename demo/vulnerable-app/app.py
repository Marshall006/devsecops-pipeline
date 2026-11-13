# ⚠️ CODE VOLONTAIREMENT VULNÉRABLE — démonstration des scanners uniquement.
import pickle
import sqlite3
import subprocess

from flask import Flask, request

app = Flask(__name__)


@app.route("/user")
def get_user():
    name = request.args.get("name")
    conn = sqlite3.connect("users.db")
    # Injection SQL : l'entrée utilisateur est concaténée dans la requête
    return str(conn.execute(f"SELECT * FROM users WHERE name = '{name}'").fetchall())


@app.route("/ping")
def ping():
    host = request.args.get("host")
    # Injection de commande : `host=8.8.8.8; rm -rf /`
    return subprocess.check_output(f"ping -c 1 {host}", shell=True)


@app.route("/load", methods=["POST"])
def load():
    # Désérialisation non sûre : exécution de code arbitraire
    return str(pickle.loads(request.data))


@app.route("/calc")
def calc():
    # Exécution de code arbitraire
    return str(eval(request.args.get("expr")))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
