from flask import jsonify, request, session
from models import UserSelection, mongo
import uuid

def register_routes(app):
    @app.route('/houses', methods=['GET'])
    def get_houses():
        houses = mongo.db.houses.find()
        return jsonify([{
            'id': str(house['_id']),
            'name': house['name'],
            'image': house.get('image', ''),
            'description': house.get('description', '')
        } for house in houses])

    @app.route('/houses/<string:house_id>/rooms', methods=['GET'])
    def get_rooms(house_id):
        rooms = mongo.db.rooms.find({'house_id': house_id})
        return jsonify([{
            'id': str(room['_id']),
            'name': room['name'],
            'color_options': room['color_options']
        } for room in rooms])

    @app.route('/select-house', methods=['POST'])
    def select_house():
        data = request.get_json()
        session_id = session.get('user_id') or str(uuid.uuid4())
        session['user_id'] = session_id
        house_id = data.get('house_id')
        house_name = data.get('house_name')

        if not house_id or not house_name:
            return jsonify({'error': 'House ID and name are required.'}), 400

        try:
            UserSelection.save_selection(session_id, house_id, house_name)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

        return jsonify({'session_id': session_id, 'house_id': house_id, 'house_name': house_name, 'rooms': []}), 201

    @app.route('/select-room', methods=['POST'])
    def select_room():
        data = request.get_json()
        session_id = session.get('user_id')
        room_id = data.get('room_id')
        room_name = data.get('room_name')
        wall_color = data.get('wall_color')
        cabinet_color = data.get('cabinet_color')

        if not session_id or not room_id or not room_name or not wall_color or not cabinet_color:
            return jsonify({'error': 'Session ID, Room ID, Room name, wall color, and cabinet color are required.'}), 400

        try:
            UserSelection.add_room_selection(session_id, room_id, room_name, wall_color, cabinet_color)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

        return jsonify({'message': 'Room selected successfully!'}), 201

    @app.route('/user/selections/<string:session_id>', methods=['GET'])
    def get_user_selections(session_id):
        user_selection = UserSelection.get_selection(session_id)
        if user_selection:
            return jsonify(user_selection), 200
        else:
            return jsonify({'message': 'No selections found for this session.'}), 404
