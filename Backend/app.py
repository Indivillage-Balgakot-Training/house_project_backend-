from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
import logging
import uuid  # Importing uuid to generate session IDs

app = Flask(__name__)
CORS(app)

# MongoDB connection
client = MongoClient('mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority') 
db = client['Dev_training']
user_choices_collection = db['user_choices']

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/api/user_choices', methods=['POST'])
def save_user_choice():
    data = request.json
    username = data.get('username')
    room_type = data.get('room_type')
    color = data.get('color')
    session_id = str(uuid.uuid4())  # Generate a unique session ID

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
        result = user_choices_collection.insert_one({
            "username": username,
            "room_type": room_type,
            "color": color,
            "session_id": session_id  # Store the session ID
        })
        logging.info("User choice saved successfully: %s", {
            "username": username, 
            "room_type": room_type, 
            "color": color, 
            "session_id": session_id,
            "id": str(result.inserted_id)
        })
        return jsonify({"message": "User choice saved successfully", "id": str(result.inserted_id), "session_id": session_id}), 201
    except Exception as e:
        logging.error("Error saving user choice: %s", e)
        return jsonify({"error": "Error saving user choice", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)  # Set debug=False in production
