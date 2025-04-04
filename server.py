import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Supported Indian indices with their Yahoo Finance symbols
INDICES = {
    'sensex': '^BSESN',        # BSE SENSEX
    'nifty50': '^NSEI',        # NIFTY 50
    'niftybank': '^NSEBANK',   # NIFTY BANK
    'bse500': '^BSE500',       # BSE 500
    'bse_midcap': 'BSEMIDCAP', # BSE MIDCAP
    'bse_smallcap': 'BSESMLCAP' # BSE SMALLCAP
}

def validate_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

def get_symbol(index_name):
    return INDICES.get(index_name.lower())

@app.route('/realtime', methods=['GET'])
def get_realtime():
    try:
        index = request.args.get('index', 'sensex')
        symbol = get_symbol(index)
        
        if not symbol:
            return jsonify({
                "error": "Invalid index",
                "available_indices": list(INDICES.keys())
            }), 400

        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        
        if data.empty:
            return jsonify({"error": "No data found"}), 404
            
        latest = data.iloc[-1]
        return jsonify({
            "index": index,
            "symbol": symbol,
            "timestamp": latest.name.isoformat(),
            "open": latest.Open,
            "high": latest.High,
            "low": latest.Low,
            "close": latest.Close,
            "volume": latest.Volume
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/historical', methods=['GET'])
def get_historical():
    try:
        index = request.args.get('index', 'sensex')
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        symbol = get_symbol(index)
        
        if not symbol:
            return jsonify({
                "error": "Invalid index",
                "available_indices": list(INDICES.keys())
            }), 400

        # Validate dates
        start = validate_date(start_date) if start_date else None
        end = validate_date(end_date) if end_date else None
        
        if (start_date and not start) or (end_date and not end):
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Get historical data
        data = yf.download(
            symbol,
            start=start,
            end=end,
            progress=False
        )
        
        if data.empty:
            return jsonify({"error": "No data found for given range"}), 404
        
        historical = [{
            "index": index,
            "symbol": symbol,
            "date": date.strftime("%Y-%m-%d"),
            "open": row.Open,
            "high": row.High,
            "low": row.Low,
            "close": row.Close,
            "volume": row.Volume
        } for date, row in data.iterrows()]
        
        return jsonify(historical)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)