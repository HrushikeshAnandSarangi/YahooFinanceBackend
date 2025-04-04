import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import logging

app = Flask(__name__)
CORS(app)
app.logger.setLevel(logging.INFO)

VALID_INDICES = {
    'sensex': {'symbol': '^BSESN', 'name': 'BSE SENSEX'},
    'nifty50': {'symbol': '^NSEI', 'name': 'NIFTY 50'},
    'niftybank': {'symbol': '^NSEBANK', 'name': 'NIFTY BANK'},
}

IST = pytz.timezone('Asia/Kolkata')
CACHE_DURATION = timedelta(minutes=5)
data_cache = {}

def get_cached_data(symbol):
    now = datetime.now(IST)
    cached = data_cache.get(symbol)
    if cached and (now - cached['timestamp']) < CACHE_DURATION:
        return cached['data']
    return None

@app.route('/indices', methods=['GET'])
def list_indices():
    return jsonify({
        "indices": {k: v['name'] for k, v in VALID_INDICES.items()},
        "updated_at": datetime.now(IST).isoformat()
    })

@app.route('/realtime', methods=['GET'])
def get_realtime():
    index = request.args.get('index', 'sensex').lower()
    
    if index not in VALID_INDICES:
        return jsonify({
            "error": "Invalid index",
            "available_indices": list(VALID_INDICES.keys())
        }), 400

    symbol = VALID_INDICES[index]['symbol']
    cached = get_cached_data(symbol)
    if cached:
        return jsonify(cached)

    try:
        ticker = yf.Ticker(symbol)
        
        # Try multiple data sources
        data = ticker.history(period='1d', interval='1m')
        if data.empty:
            data = ticker.history(period='5d', interval='1d')
        
        if data.empty:
            app.logger.warning(f"No data available for {symbol}")
            return jsonify({
                "status": "unavailable",
                "index": index,
                "message": "Data source temporarily unavailable"
            }), 503

        latest = data.iloc[-1]
        timestamp = latest.name.astimezone(IST)
        
        response = {
            "index": index,
            "name": VALID_INDICES[index]['name'],
            "timestamp": timestamp.isoformat(),
            "open": round(latest.Open, 2),
            "high": round(latest.High, 2),
            "low": round(latest.Low, 2),
            "close": round(latest.Close, 2),
            "volume": int(latest.Volume),
            "status": "live"
        }
        
        # Cache successful response
        data_cache[symbol] = {
            'data': response,
            'timestamp': datetime.now(IST)
        }
        
        return jsonify(response)

    except Exception as e:
        app.logger.error(f"API failure for {symbol}: {str(e)}")
        return jsonify({
            "status": "error",
            "index": index,
            "message": "Financial data service unavailable"
        }), 503

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)