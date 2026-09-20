"""Agente Zeus — Dashboard do bot de criptomoedas.

App Flask com:
  - Preços ao vivo (API pública CoinGecko)
  - Carteira (portfolio) salva em SQLite
  - Histórico de preços simples
  - Alertas de preço (acima/abaixo de um valor)
  - "Bot" que verifica os alertas a cada refresh

Rodar localmente:
    pip install -r requirements.txt
    python app.py
Acesse http://localhost:5000
"""

import sqlite3
import time
import threading

import requests
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

DB_PATH = "crypto.db"
COINGECKO_MARKETS = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false"
)

app = Flask(__name__)
app.secret_key = "troque-por-uma-chave-secreta"


# ---------------------------------------------------------------- banco
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL UNIQUE,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                price REAL NOT NULL,
                ts REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL CHECK (direction IN ('acima', 'abaixo')),
                threshold REAL NOT NULL,
                triggered INTEGER NOT NULL DEFAULT 0,
                message TEXT
            );
            """
        )


# ---------------------------------------------------------------- preços
def fetch_market():
    """Busca as top moedas na CoinGecko. Retorna lista de dicts."""
    try:
        resp = requests.get(COINGECKO_MARKETS, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []


def save_history(market):
    now = time.time()
    with db() as conn:
        for c in market:
            conn.execute(
                "INSERT INTO price_history (coin_id, price, ts) VALUES (?,?,?)",
                (c["id"], c["current_price"], now),
            )
        conn.commit()


def check_alerts(market):
    """O 'bot': dispara alertas cujo preço cruzou o limiar."""
    price_by_id = {c["id"]: c["current_price"] for c in market}
    fired = []
    with db() as conn:
        for a in conn.execute("SELECT * FROM alerts WHERE triggered = 0").fetchall():
            price = price_by_id.get(a["coin_id"])
            if price is None:
                continue
            hit = (
                a["direction"] == "acima" and price >= a["threshold"]
            ) or (a["direction"] == "abaixo" and price <= a["threshold"])
            if hit:
                msg = f"{a['symbol']} {a['direction']} de ${a['threshold']:,.2f} — preço atual ${price:,.2f}"
                conn.execute(
                    "UPDATE alerts SET triggered = 1, message = ? WHERE id = ?",
                    (msg, a["id"]),
                )
                fired.append(msg)
        conn.commit()
    return fired


# ---------------------------------------------------------------- helpers
def portfolio_rows(market):
    price_by_id = {c["id"]: c["current_price"] for c in market}
    with db() as conn:
        rows = conn.execute("SELECT * FROM portfolio ORDER BY symbol").fetchall()
    total = 0.0
    items = []
    for r in rows:
        price = price_by_id.get(r["coin_id"], 0.0)
        value = price * r["amount"]
        total += value
        items.append(dict(r, price=price, value=value))
    return items, total


def price_history(coin_id, limit=24):
    with db() as conn:
        rows = conn.execute(
            "SELECT price, ts FROM price_history WHERE coin_id = ? ORDER BY ts DESC LIMIT ?",
            (coin_id, limit),
        ).fetchall()
    return [(r["ts"], r["price"]) for r in reversed(rows)]


# ---------------------------------------------------------------- rotas
@app.route("/")
def index():
    market = fetch_market()
    if market:
        save_history(market)
    fired = check_alerts(market)
    for msg in fired:
        flash(f"🔔 Alerta disparado: {msg}")
    portfolio, total = portfolio_rows(market)
    with db() as conn:
        alerts = conn.execute("SELECT * FROM alerts ORDER BY triggered, id DESC").fetchall()
    return render_template(
        "index.html", market=market, portfolio=portfolio, total=total, alerts=alerts
    )


@app.post("/portfolio/add")
def portfolio_add():
    coin_id = request.form.get("coin_id", "").strip()
    amount = float(request.form.get("amount") or 0)
    market = fetch_market()
    coin = next((c for c in market if c["id"] == coin_id), None)
    if coin and amount > 0:
        with db() as conn:
            conn.execute(
                "INSERT INTO portfolio (coin_id, symbol, name, amount) VALUES (?,?,?,?) "
                "ON CONFLICT(coin_id) DO UPDATE SET amount = amount + ?",
                (coin_id, coin["symbol"].upper(), coin["name"], amount, amount),
            )
            conn.commit()
        flash(f"Adicionado {amount:g} {coin['symbol'].upper()} à carteira.")
    return redirect(url_for("index"))


@app.post("/portfolio/remove/<int:item_id>")
def portfolio_remove(item_id):
    with db() as conn:
        conn.execute("DELETE FROM portfolio WHERE id = ?", (item_id,))
        conn.commit()
    return redirect(url_for("index"))


@app.post("/alerts/add")
def alerts_add():
    coin_id = request.form.get("coin_id", "").strip()
    direction = request.form.get("direction", "acima")
    threshold = float(request.form.get("threshold") or 0)
    market = fetch_market()
    coin = next((c for c in market if c["id"] == coin_id), None)
    if coin and threshold > 0:
        with db() as conn:
            conn.execute(
                "INSERT INTO alerts (coin_id, symbol, direction, threshold) VALUES (?,?,?,?)",
                (coin_id, coin["symbol"].upper(), direction, threshold),
            )
            conn.commit()
        flash(f"Alerta criado: {coin['symbol'].upper()} {direction} de ${threshold:,.2f}")
    return redirect(url_for("index"))


@app.post("/alerts/remove/<int:alert_id>")
def alerts_remove(alert_id):
    with db() as conn:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
    return redirect(url_for("index"))


@app.get("/api/prices")
def api_prices():
    return jsonify(fetch_market())


@app.get("/api/history/<coin_id>")
def api_history(coin_id):
    return jsonify(price_history(coin_id))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
