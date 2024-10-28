from flask import Flask, jsonify, redirect, url_for, send_from_directory
from flask_pymongo import PyMongo
from flask_cors import CORS  # Import CORS for cross-origin requests
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# MongoDB connection string
app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

@app.route('/', methods=['GET'])
def home():
    return redirect(url_for('get_houses'))

@app.route('/page.tsx', methods=['GET'])
def page():
    return send_from_directory(r'C:\Users\Acer 7\Desktop\House\House-Project\src\app', 'page.tsx')

@app.route('/houses', methods=['GET'])
def get_houses():
    houses = mongo.db.houses.find()  # Fetch houses from MongoDB
    house_list = [
        {
            'id': str(house['_id']),
            'name': f"House Number {i + 1}",  # Sequential naming
            'image': f"house {i + 1}.gallery.jpg",  # Make sure this matches the image filenames
            'description': house.get('description', '')
        }
        for i, house in enumerate(houses)
        if i < 4  # Limit to 4 houses
    ]
    return jsonify(house_list)

@app.route('/houses/<string:house_id>/rooms', methods=['GET'])
def get_rooms(house_id):
    rooms = mongo.db.rooms.find({'house_id': house_id})  # Fetch rooms for the specific house
    return jsonify([{'id': str(room['_id']), 'name': room['name'], 'color_options': room['color_options']} for room in rooms])

if __name__ == '__main__':
    app.run(debug=True)
