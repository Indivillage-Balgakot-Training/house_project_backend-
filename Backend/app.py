from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

# MongoDB connection
client = MongoClient('mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority') # Replace with your connection URL if needed
db = client['Dev_training']
areas_collection = db['areas']  # Collection name

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/api/areas', methods=['POST'])
def save_area():
    data = request.json
    area = data.get('area')
    color = data.get('color')

    # Input validation
    if not area or not isinstance(area, str):
        logging.warning("Invalid or missing 'area' in request: %s", data)
        return jsonify({"message": "Area must be a non-empty string"}), 400

    if not color or not isinstance(color, str):
        logging.warning("Invalid or missing 'color' in request: %s", data)
        return jsonify({"message": "Color must be a non-empty string"}), 400

    try:
        # Insert into MongoDB
        result = areas_collection.insert_one({"area": area, "color": color})
        logging.info("Area saved successfully: %s", {"area": area, "color": color, "id": str(result.inserted_id)})
        return jsonify({"message": "Area saved successfully", "id": str(result.inserted_id)}), 201
    except Exception as e:
        logging.error("Error saving area: %s", e)
        return jsonify({"message": "Error saving area", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
