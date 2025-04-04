from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
from datetime import datetime

app = Flask(__name__)
CORS(app)  
BSE_SYMBOL = "^BSESN"

def validate_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

@app.route('/realtime', methods=['GET'])
def get_realtime():
    try:
        ticker = yf.Ticker(BSE_SYMBOL)
        data = ticker.history(period="1d")
        
        if data.empty:
            return jsonify({"error": "No data found"}), 404
            
        latest = data.iloc[-1]
        return jsonify({
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
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        start = validate_date(start_date) if start_date else None
        end = validate_date(end_date) if end_date else None
        
        if (start_date and not start) or (end_date and not end):
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        data = yf.download(
            BSE_SYMBOL,
            start=start,
            end=end,
            progress=False
        )
        
        if data.empty:
            return jsonify({"error": "No data found for given range"}), 404
        historical = [{
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
    app.run(debug=True, port=5000)