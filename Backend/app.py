from flask import Flask, jsonify, redirect, url_for, request
from flask_pymongo import PyMongo
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app)

app.config["MONGO_URI"] = "mongodb+srv://Balgakot_app_training:SBhQqTzY7Go7sEXJ@validationapp.63rbg.mongodb.net/Dev_training?retryWrites=true&w=majority"
mongo = PyMongo(app)

@app.route('/', methods=['GET'])
def home():
    return redirect(url_for('get_houses'))

def serialize_house(house):
    return {
        'id': str(house['_id']),
        'name': house['name'],
        'image': house.get('image', ''),
        'description': house.get('description', '')
    }

@app.route('/houses', methods=['GET'])
def get_houses():
    houses = mongo.db.houses.find()
    house_list = [serialize_house(house) for house in houses][:4]
    return jsonify(house_list)

@app.route('/houses/<string:house_id>/rooms', methods=['GET'])
def get_rooms(house_id):
    rooms = mongo.db.rooms.find({'house_id': house_id})
    return jsonify([{
        'id': str(room['_id']),
        'name': room['name'],
        'color_options': room['color_options'],
        'image': room.get('image', '')
    } for room in rooms])

@app.route('/select-house', methods=['POST'])
def select_house():
    data = request.get_json()
    session_id = data.get('session_id') or str(uuid.uuid4())
    house_id = data.get('house_id')
    house_name = data.get('house_name')

    if not house_id or not house_name:
        return jsonify({'error': 'House ID and name are required.'}), 400

    try:
        mongo.db.user_choices.update_one(
            {'session_id': session_id},
            {'$set': {'house_id': house_id, 'house_name': house_name, 'rooms': []}},
            upsert=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'session_id': session_id, 'house_id': house_id, 'house_name': house_name, 'rooms': []}), 201

@app.route('/select-room', methods=['POST'])
def select_room():
    data = request.get_json()
    session_id = data.get('session_id')
    room_id = data.get('room_id')
    room_name = data.get('room_name')
    wall_color = data.get('wall_color')
    cabinet_color = data.get('cabinet_color')

    if not session_id or not room_id or not room_name or not wall_color or not cabinet_color:
        return jsonify({'error': 'All fields are required.'}), 400

    try:
        mongo.db.user_choices.update_one(
            {'session_id': session_id},
            {
                '$addToSet': {
                    'rooms': {
                        'room_id': room_id,
                        'room_name': room_name,
                        'wall_color': wall_color,
                        'cabinet_color': cabinet_color
                    }
                }
            },
            upsert=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'Room selected successfully!'}), 201


@app.route('/user/selections/<string:session_id>', methods=['GET'])
def get_user_selections(session_id):
    user_choice = mongo.db.user_choices.find_one({'session_id': session_id})
    if user_choice:
        return jsonify(user_choice), 200
    else:
        return jsonify({'message': 'No selections found for this session.'}), 404

@app.route('/kitchen/images', methods=['GET'])
def get_kitchen_images():
    kitchen_images = [
        {'name': 'Default', 'image': '/images/kitchen.jpg', 'color': '#FAF0E6'},
        {'name': 'Caramel', 'image': '/images/kitchenCabinet1.jpg', 'color': '#D2B48C'},
        {'name': 'Yellow', 'image': '/images/kitchenCabinet2.jpg', 'color': '#FFD700'},
        {'name': 'Neon Pink', 'image': '/images/kitchenCabinet3.jpg', 'color': '#FF69B4'},
    ]
    
    wall_images = [
        {'name': 'Pale Green', 'image': '/images/Wall1.jpg', 'color': '#b0c8bf'},
        {'name': 'Pale Olive', 'image': '/images/Wall2.jpg', 'color': '#dad8b9'},
        {'name': 'Warm Beige', 'image': '/images/Wall3.jpg', 'color': '#c8bca6'},
    ]

    combined_images = {
        'cabinets': kitchen_images,
        'walls': wall_images
    }
    
    return jsonify(combined_images)

if __name__ == '__main__':
    app.run(debug=True)
