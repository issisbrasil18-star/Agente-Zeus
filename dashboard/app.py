"""Agente Zeus — Dashboard do bot de criptomoedas.

App Flask com:
  - Preços ao vivo (API pública CoinGecko, variação 24h e 7d)
  - Carteira (portfolio) salva em SQLite
  - Histórico de preços
  - Alertas de preço (acima/abaixo de um valor) e de variação (24h %)
  - Análise do agente: sentimento do mercado, destaques e leitura da carteira

Rodar localmente:
    pip install -r requirements.txt
    python app.py
Acesse http://localhost:5000
"""

import os
import sqlite3
import time

import requests

# cache simples das cotações (TTL em segundos) para respeitar o
# rate limit da API gratuita da CoinGecko
_cache = {"data": None, "ts": 0.0}
CACHE_TTL = 60
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

DB_PATH = "crypto.db"
COINGECKO_MARKETS = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd&order=market_cap_desc&per_page=20&page=1"
    "&sparkline=false&price_change_percentage=24h,7d"
)

app = Flask(__name__)

# Em produção: export FLASK_SECRET_KEY=<chave gerada com `python -c "import os; print(os.urandom(32).hex())"`>
# Sem a variável, uma chave aleatória é gerada a cada execução (as sessões
# não sobrevivem a um restart, mas nenhuma chave fica exposta no código).
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32).hex()


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
                kind TEXT NOT NULL DEFAULT 'preco',
                direction TEXT NOT NULL CHECK (direction IN ('acima', 'abaixo')),
                threshold REAL NOT NULL,
                triggered INTEGER NOT NULL DEFAULT 0,
                message TEXT
            );
            """
        )
        # migração de bancos antigos: coluna 'kind'
        cols = [r[1] for r in conn.execute("PRAGMA table_info(alerts)")]
        if "kind" not in cols:
            conn.execute("ALTER TABLE alerts ADD COLUMN kind TEXT NOT NULL DEFAULT 'preco'")
        conn.commit()


# ---------------------------------------------------------------- preços
def fetch_market():
    """Busca as top moedas na CoinGecko, com cache de 60s.

    Em caso de erro devolve o último resultado válido (ou lista vazia).
    """
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < CACHE_TTL:
        return _cache["data"]
    try:
        resp = requests.get(COINGECKO_MARKETS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _cache["data"], _cache["ts"] = data, now
        return data
    except Exception:
        return _cache["data"] or []


def save_history(market):
    now = time.time()
    with db() as conn:
        for c in market:
            conn.execute(
                "INSERT INTO price_history (coin_id, price, ts) VALUES (?,?,?)",
                (c["id"], c["current_price"], now),
            )
        conn.commit()


# ---------------------------------------------------------------- agente
def check_alerts(market):
    """O 'bot': dispara alertas cuja condição foi atingida."""
    price_by_id = {c["id"]: c["current_price"] for c in market}
    pct_by_id = {c["id"]: (c.get("price_change_percentage_24h") or 0) for c in market}
    fired = []
    with db() as conn:
        for a in conn.execute("SELECT * FROM alerts WHERE triggered = 0").fetchall():
            if a["kind"] == "variacao":
                value = pct_by_id.get(a["coin_id"])
                label = f"{a['symbol']} variou {value:+.2f}% em 24h"
            else:
                value = price_by_id.get(a["coin_id"])
                label = f"{a['symbol']} está a ${value:,.2f}" if value is not None else a["symbol"]
            if value is None:
                continue
            hit = (a["direction"] == "acima" and value >= a["threshold"]) or (
                a["direction"] == "abaixo" and value <= a["threshold"]
            )
            if hit:
                unit = "%" if a["kind"] == "variacao" else "$"
                msg = f"{label} — gatilho: {a['direction']} de {unit}{a['threshold']:,.2f}"
                conn.execute(
                    "UPDATE alerts SET triggered = 1, message = ? WHERE id = ?",
                    (msg, a["id"]),
                )
                fired.append(msg)
        conn.commit()
    return fired


def pct(c):
    """Variação 24h de uma moeda do mercado (0 se indisponível)."""
    return (c.get("price_change_percentage_24h") or 0)


def agent_analysis(market, portfolio):
    """A análise do agente: sentimento, destaques e leitura da carteira."""
    if not market:
        return None

    pct7 = lambda c: (c.get("price_change_percentage_7d_in_currency") or 0)
    ups = [c for c in market if pct(c) >= 0]
    downs = [c for c in market if pct(c) < 0]

    sorted_24h = sorted(market, key=pct)
    top_gainers = sorted_24h[-3:][::-1]
    top_losers = sorted_24h[:3]

    if len(ups) >= len(market) * 0.7:
        sentiment = "otimista"
        sentiment_note = "A maioria das top 20 está subindo — mercado em alta."
    elif len(downs) >= len(market) * 0.7:
        sentiment = "pessimista"
        sentiment_note = "A maioria das top 20 está caindo — cuidado com compras hoje."
    else:
        sentiment = "neutro"
        sentiment_note = "Mercado misto, sem direção clara nas top 20."

    notes = []
    if portfolio:
        price_by_id = {c["id"]: c for c in market}
        pl_24h = 0.0
        worst = best = None
        for p in portfolio:
            c = price_by_id.get(p["coin_id"])
            if not c:
                continue
            change = pct(c) * p["value"] / 100
            pl_24h += change
            if best is None or change > best[1]:
                best = (p["symbol"], change, pct(c))
            if worst is None or change < worst[1]:
                worst = (p["symbol"], change, pct(c))
        if pl_24h >= 0:
            notes.append(
                f"Sua carteira está estimada em +${pl_24h:,.2f} nas últimas 24h."
            )
        else:
            notes.append(
                f"Sua carteira está estimada em -${abs(pl_24h):,.2f} nas últimas 24h."
            )
        if best:
            notes.append(f"Melhor posição: {best[0]} ({best[2]:+.2f}% em 24h).")
        if worst and worst[0] != best[0]:
            notes.append(f"Pior posição: {worst[0]} ({worst[2]:+.2f}% em 24h).")
    else:
        notes.append("Carteira vazia — adicione moedas para o agente analisar suas posições.")

    return {
        "sentiment": sentiment,
        "sentiment_note": sentiment_note,
        "ups": len(ups),
        "downs": len(downs),
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "notes": notes,
    }


# ---------------------------------------------------------------- helpers
def portfolio_rows(market):
    price_by_id = {c["id"]: c for c in market}
    total = 0.0
    items = []
    with db() as conn:
        rows = conn.execute("SELECT * FROM portfolio ORDER BY symbol").fetchall()
    for r in rows:
        c = price_by_id.get(r["coin_id"], {})
        price = c.get("current_price", 0.0)
        value = price * r["amount"]
        total += value
        items.append(dict(r, price=price, value=value, change_24h=pct(c) if c else 0))
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
    analysis = agent_analysis(market, portfolio)
    with db() as conn:
        alerts = conn.execute(
            "SELECT * FROM alerts ORDER BY triggered, id DESC"
        ).fetchall()
    return render_template(
        "index.html",
        market=market,
        portfolio=portfolio,
        total=total,
        alerts=alerts,
        analysis=analysis,
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
    kind = request.form.get("kind", "preco")
    direction = request.form.get("direction", "acima")
    threshold = float(request.form.get("threshold") or 0)
    market = fetch_market()
    coin = next((c for c in market if c["id"] == coin_id), None)
    if coin and threshold > 0 and kind in ("preco", "variacao"):
        with db() as conn:
            conn.execute(
                "INSERT INTO alerts (coin_id, symbol, kind, direction, threshold) "
                "VALUES (?,?,?,?,?)",
                (coin_id, coin["symbol"].upper(), kind, direction, threshold),
            )
            conn.commit()
        unit = "%" if kind == "variacao" else "$"
        flash(f"Alerta criado: {coin['symbol'].upper()} {direction} de {unit}{threshold:,.2f}")
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


@app.get("/api/analysis")
def api_analysis():
    portfolio, _ = portfolio_rows(fetch_market())
    return jsonify(agent_analysis(fetch_market(), portfolio))


if __name__ == "__main__":
    init_db()
    # debug nunca fica ligado por padrão; em produção use um servidor WSGI
    # (ex.: gunicorn) em vez de `python app.py`
    debug = os.environ.get("FLASK_DEBUG") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug, port=port)
