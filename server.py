import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
CORS(app)

# Valid Indian indices with verified Yahoo Finance symbols
VALID_INDICES = {
    'sensex': {'symbol': '^BSESN', 'name': 'BSE SENSEX'},
    'nifty50': {'symbol': '^NSEI', 'name': 'NIFTY 50'},
    'niftybank': {'symbol': '^NSEBANK', 'name': 'NIFTY BANK'},
    # Removed unavailable indices with invalid symbols
}

IST = pytz.timezone('Asia/Kolkata')

def validate_dates(start, end):
    """Validate date range constraints"""
    if start and end and start > end:
        return False
    max_range = timedelta(days=365*5)  # 5 years max
    if start and end and (end - start) > max_range:
        return False
    return True

@app.route('/indices', methods=['GET'])
def list_indices():
    """Endpoint to list available indices"""
    return jsonify({
        "indices": {k: v['name'] for k, v in VALID_INDICES.items()}
    })

@app.route('/realtime', methods=['GET'])
def get_realtime():
    index = request.args.get('index', 'sensex').lower()
    
    if index not in VALID_INDICES:
        return jsonify({
            "error": "Invalid index",
            "available_indices": list(VALID_INDICES.keys())
        }), 400

    try:
        symbol = VALID_INDICES[index]['symbol']
        ticker = yf.Ticker(symbol)
        
        # Get latest data with 1 minute interval
        data = ticker.history(period='1d', interval='1m')
        
        if data.empty:
            app.logger.warning(f"No data found for {symbol}")
            return jsonify({
                "error": "No recent data available",
                "index": index
            }), 404
            
        latest = data.iloc[-1]
        timestamp = latest.name.astimezone(IST)

        return jsonify({
            "index": index,
            "name": VALID_INDICES[index]['name'],
            "timestamp": timestamp.isoformat(),
            "open": round(latest.Open, 2),
            "high": round(latest.High, 2),
            "low": round(latest.Low, 2),
            "close": round(latest.Close, 2),
            "volume": int(latest.Volume)
        })

    except Exception as e:
        app.logger.error(f"Error in /realtime: {str(e)}")
        return jsonify({
            "error": "Failed to fetch realtime data",
            "details": "Service temporarily unavailable"
        }), 500

@app.route('/historical', methods=['GET'])
def get_historical():
    index = request.args.get('index', 'sensex').lower()
    start = request.args.get('start')
    end = request.args.get('end') or datetime.now(IST).strftime('%Y-%m-%d')

    if index not in VALID_INDICES:
        return jsonify({
            "error": "Invalid index",
            "available_indices": list(VALID_INDICES.keys())
        }), 400

    try:
        # Date parsing with timezone awareness
        start_date = datetime.strptime(start, '%Y-%m-%d').replace(tzinfo=IST) if start else None
        end_date = datetime.strptime(end, '%Y-%m-%d').replace(tzinfo=IST) + timedelta(days=1)
        
        if not validate_dates(start_date, end_date):
            return jsonify({"error": "Date range exceeds 5 years or invalid"}), 400

        # Fetch historical data
        symbol = VALID_INDICES[index]['symbol']
        data = yf.download(
            symbol,
            start=start_date,
            end=end_date,
            progress=False
        )

        if data.empty:
            return jsonify({
                "error": "No historical data found",
                "index": index,
                "date_range": f"{start} to {end}"
            }), 404

        # Process response
        historical = []
        for date, row in data.iterrows():
            date_ist = date.tz_localize('UTC').tz_convert(IST) if date.tzinfo is None else date.astimezone(IST)
            historical.append({
                "date": date_ist.strftime('%Y-%m-%d'),
                "open": round(row['Open'], 2),
                "high": round(row['High'], 2),
                "low": round(row['Low'], 2),
                "close": round(row['Close'], 2),
                "volume": int(row['Volume'])
            })

        return jsonify({
            "index": index,
            "name": VALID_INDICES[index]['name'],
            "data": historical
        })

    except ValueError as e:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    except Exception as e:
        app.logger.error(f"Historical data error: {str(e)}")
        return jsonify({
            "error": "Failed to fetch historical data",
            "details": "Check date parameters or try again later"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)