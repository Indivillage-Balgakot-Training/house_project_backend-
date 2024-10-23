from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

# MongoDB connection
client = MongoClient('mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority') 
db = client['Dev_training']
areas_collection = db['areas']  # Collection for areas
user_choices_collection = db['user_choices']  # Collection for user choices

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
        return jsonify({"error": "Area must be a non-empty string"}), 400

    if not color or not isinstance(color, str):
        logging.warning("Invalid or missing 'color' in request: %s", data)
        return jsonify({"error": "Color must be a non-empty string"}), 400

    try:
        # Insert into MongoDB
        result = areas_collection.insert_one({"area": area, "color": color})
        logging.info("Area saved successfully: %s", {"area": area, "color": color, "id": str(result.inserted_id)})
        return jsonify({"message": "Area saved successfully", "id": str(result.inserted_id)}), 201
    except Exception as e:
        logging.error("Error saving area: %s", e)
        return jsonify({"error": "Error saving area", "details": str(e)}), 500

@app.route('/api/user_choices', methods=['POST'])
def save_user_choice():
    data = request.json
    username = data.get('username')
    room_type = data.get('room_type')  # e.g., kitchen, bedroom
    color = data.get('color')

    # Input validation
    if not username or not isinstance(username, str):
        logging.warning("Invalid or missing 'username' in request: %s", data)
        return jsonify({"error": "Username must be a non-empty string"}), 400

    if not room_type or not isinstance(room_type, str):
        logging.warning("Invalid or missing 'room_type' in request: %s", data)
        return jsonify({"error": "Room type must be a non-empty string"}), 400

    if not color or not isinstance(color, str):
        logging.warning("Invalid or missing 'color' in request: %s", data)
        return jsonify({"error": "Color must be a non-empty string"}), 400

    try:
        # Insert user choice into MongoDB
        result = user_choices_collection.insert_one({
            "username": username,
            "room_type": room_type,
            "color": color
        })
        logging.info("User choice saved successfully: %s", {
            "username": username, 
            "room_type": room_type, 
            "color": color, 
            "id": str(result.inserted_id)
        })
        return jsonify({"message": "User choice saved successfully", "id": str(result.inserted_id)}), 201
    except Exception as e:
        logging.error("Error saving user choice: %s", e)
        return jsonify({"error": "Error saving user choice", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)  # Set debug=False in production
