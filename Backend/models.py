from flask_pymongo import PyMongo
from pymongo.errors import PyMongoError

mongo = PyMongo()

class UserSelection:
    @staticmethod
    def save_selection(session_id, house_id, house_name):
        mongo.db.user_choices.update_one(
            {'session_id': session_id},
            {'$set': {
                'house_id': house_id,
                'house_name': house_name,
                'rooms': []  # Initialize rooms list
            }},
            upsert=True
        )

    @staticmethod
    def add_room_selection(session_id, room_id, room_name, wall_color, cabinet_color):
        # Validate input
        if not all([session_id, room_id, room_name, wall_color, cabinet_color]):
            raise ValueError("All parameters must be provided and cannot be empty.")

        try:
            mongo.db.user_choices.update_one(
                {'session_id': session_id, 'rooms.room_id': room_id},
                {
                    '$set': {
                        'rooms.$.wall_color': wall_color,
                        'rooms.$.cabinet_color': cabinet_color,
                    },
                    '$setOnInsert': {
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
        except PyMongoError as e:
            raise Exception(f"Database error: {str(e)}")

    @staticmethod
    def get_selection(session_id):
        return mongo.db.user_choices.find_one({'session_id': session_id})
