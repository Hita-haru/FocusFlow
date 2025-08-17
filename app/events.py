from flask_login import current_user
from flask_socketio import join_room, leave_room, emit
from . import socketio, db
from .models import FocusRoom

@socketio.on('join')
def on_join(data):
    room_id = data['room_id']
    room = FocusRoom.query.get(room_id)
    username = current_user.username
    
    if room is None or current_user not in room.participants:
        return

    join_room(room_id)
    emit('room_message', {'msg': f'{username} has entered the room.'}, to=room_id)

@socketio.on('leave')
def on_leave(data):
    room_id = data['room_id']
    username = current_user.username
    
    leave_room(room_id)
    emit('room_message', {'msg': f'{username} has left the room.'}, to=room_id)

@socketio.on('update_status')
def on_update_status(data):
    room_id = data['room_id']
    room = FocusRoom.query.get(room_id)
    
    if room is None or current_user not in room.participants:
        return

    current_user.status = data.get('status', current_user.status)
    current_user.current_gauge_level = int(data.get('gauge_level', 0))
    db.session.commit()

    emit('status_updated', {
        'username': current_user.username,
        'status': current_user.status,
        'gauge_level': current_user.current_gauge_level
    }, to=room_id, include_self=False)
