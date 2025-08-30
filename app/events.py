from flask_login import current_user
from flask_socketio import join_room, leave_room, emit
from . import socketio, db
from .models import FocusRoom, ChatMessage

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

@socketio.on('room_chat')
def on_room_chat(data):
    room_id = data.get('room_id')
    msg = data.get('msg', '').strip()
    room = FocusRoom.query.get(room_id)
    
    # 5文字以上、いないユーザーのメッセージは無視
    if not msg or len(msg) > 5:
        return

    if room is None or current_user not in room.participants:
        return

    new_message = ChatMessage(room_id=room_id, user_id=current_user.id, message=msg)
    db.session.add(new_message)
    db.session.commit()

    emit('new_chat_message', {
        'username': current_user.username,
        'msg': msg
    }, to=room_id)
