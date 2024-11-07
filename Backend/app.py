from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import os

app = Flask(__name__)
CORS(app)  # Enable CORS

# Set up MongoDB connection (assuming MongoDB is running locally)
client = MongoClient("mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority")
db = client['Dev_training']  # Replace with your database name
houses_collection = db['houses']  # Replace with your collection name_

@app.route('/houses', methods=['GET'])
def get_houses():
    try:
        # Fetch all houses from MongoDB
        houses = list(houses_collection.find({}, {'_id': 0}))  # Exclude MongoDB _id field
        if houses:
            # Add the relative image paths to each house object
            for house in houses:
                house['image_path'] = f"/{house['house_image']}"  # Assuming house_image is the field with image name
            return jsonify(houses), 200
        else:
            return jsonify({'message': 'No houses found'}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Error fetching houses'}), 500

@app.route('/select-house', methods=['POST'])
def select_house():
    try:
        # Get house data from the request
        data = request.get_json()
        house_id = data.get('house_id')
        house_name = data.get('house_name')

        if not house_id or not house_name:
            return jsonify({'error': 'House ID and Name are required'}), 400
        
        # You can handle storing the selected house in a database or some logic here
        # For now, just return a success message
        return jsonify({'message': f'House {house_name} selected successfully'}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Error processing house selection'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)  # Run the Flask app on port 5000
