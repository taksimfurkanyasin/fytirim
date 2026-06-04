"""
Portfolio Tracker - Local Backend Server
Run with: python server.py
Then open: http://localhost:5000
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route("/")
def index():
    return send_from_directory(SCRIPT_DIR, "portfolio_tracker.html")

@app.route("/ping")
def ping():
    return "ok", 200


@app.route("/prices")
def get_prices():
    """
    Current prices: /prices?tickers=AMZN,USDTRY=X,SI=F
    Returns { ticker: { price, prevClose, currency } }
    """
    tickers_param = request.args.get("tickers", "")
    tickers = [t.strip() for t in tickers_param.split(",") if t.strip()]
    if not tickers:
        return jsonify({"error": "No tickers provided"}), 400

    results = {}
    for ticker in tickers:
        try:
            t  = yf.Ticker(ticker)
            fi = t.fast_info
            price      = fi.last_price
            prev_close = fi.previous_close
            currency   = getattr(fi, "currency", "USD")

            if price is None:
                hist = t.history(period="5d")
                if not hist.empty:
                    price      = float(hist["Close"].iloc[-1])
                    prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
                    currency   = t.info.get("currency", "USD")

            if price is not None:
                results[ticker] = {
                    "price":     float(price),
                    "prevClose": float(prev_close) if prev_close else float(price),
                    "currency":  str(currency) if currency else "USD",
                }
        except Exception as e:
            print(f"  [ERROR] {ticker}: {e}")

    print(f"  /prices  {len(results)}/{len(tickers)} tickers")
    return jsonify(results)


@app.route("/history")
def get_history():
    """
    Historical daily closes for a date range.
    /history?tickers=AMZN,PGSUS.IS,USDTRY%3DX,SI%3DF&start=2024-01-01&end=2025-05-31
    Returns {
      ticker: { "2024-01-02": 185.20, "2024-01-03": 187.10, ... },
      ...
    }
    Dates are trading days only (non-trading days are forward-filled by the client).
    """
    tickers_param = request.args.get("tickers", "")
    start         = request.args.get("start", "")
    end           = request.args.get("end",   "")
    tickers       = [t.strip() for t in tickers_param.split(",") if t.strip()]

    if not tickers or not start:
        return jsonify({"error": "tickers and start are required"}), 400

    results = {}
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(start=start, end=end or None)
            if hist.empty:
                continue
            # Forward-fill weekends / holidays so client can use any date
            idx_full = pd.date_range(start=hist.index[0], end=hist.index[-1], freq="D")
            hist     = hist.reindex(idx_full).ffill()
            closes   = {str(d.date()): round(float(v), 6) for d, v in hist["Close"].items() if not pd.isna(v)}
            if closes:
                results[ticker] = closes
        except Exception as e:
            print(f"  [ERROR] history {ticker}: {e}")

    print(f"  /history {len(results)}/{len(tickers)} tickers  {start}→{end or 'today'}")
    return jsonify(results)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print(f"  Portfolio Tracker running on port {port}!")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=port)
