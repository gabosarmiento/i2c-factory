# app.py

from flask import Flask, request, jsonify

app = Flask(__name__)

# Simulated endpoint consuming a weather API
@app.route("/weather")
def get_weather():
    city = request.args.get("city", "Paris")
    # Fake response for demo; normally you'd call requests.get() here
    fake_weather = {
        "Paris": {"temperature": 18, "condition": "Cloudy"},
        "Tokyo": {"temperature": 23, "condition": "Sunny"},
        "New York": {"temperature": 16, "condition": "Rainy"},
    }
    data = fake_weather.get(city, {"temperature": "unknown", "condition": "unknown"})
    return jsonify({"city": city, **data})

if __name__ == "__main__":
    app.run(debug=True)
