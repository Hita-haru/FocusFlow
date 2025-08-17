# FocusFlow開発チュートリアル - フォーカスルーム編（コードあり）

このチュートリアルでは、FocusFlowに複数人のユーザーが同時に集中できる「フォーカスルーム」機能を実装する手順を、具体的なコード例と共に解説します。

## 1. コンセプト：静かなる共闘空間

フォーカスルームは、同じ目標を持つ仲間と**「静かに、共に集中する」**ための空間です。核心技術は**WebSocket**によるリアルタイム通信です。

## 2. ライブラリのインストール

まず、リアルタイム通信を実現するためのライブラリをインストールします。

```bash
pip install Flask-SocketIO
```

---

## Step 1: データベース設計 (`app/models.py`)

ルームの情報と、ユーザーとルームの関係を定義します。

### `app/models.py` の全体像

既存の`followers`テーブルの下に、新しい中間テーブル`room_participants`を追加し、`FocusRoom`モデルを新設します。また、`User`モデルにリレーションシップを追加します。

```python
# app/models.py

from flask_login import UserMixin
from . import db
from werkzeug.security import generate_password_hash, check_password_hash

# フォロー関係の中間テーブル (既存)
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

# ★【新規】ルーム参加者の中間テーブル
room_participants = db.Table('room_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('room_id', db.Integer, db.ForeignKey('focus_room.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    # ... 既存のカラム定義 ...
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128))
    sessions = db.relationship('FocusSession', backref='author', lazy=True)
    flow_state_logs = db.relationship('FlowStateLog', backref='user', lazy=True)
    status = db.Column(db.String(50), default='オフライン')
    current_gauge_level = db.Column(db.Integer, default=0)

    # ... 既存のfollowedリレーションシップ ...
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    # ★【追加】ルームとのリレーションシップ
    # 自身が作成したルーム (1対多)
    created_rooms = db.relationship('FocusRoom', backref='owner', lazy='dynamic')
    # 参加しているルーム (多対多)
    joined_rooms = db.relationship('FocusRoom', secondary=room_participants, lazy='dynamic',
                                   backref=db.backref('participants', lazy='dynamic'))

    # ... 既存のメソッド ...


class FocusSession(db.Model):
    # ... 変更なし ...
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(200), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class FlowStateLog(db.Model):
    # ... 変更なし ...
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# ★【新規】FocusRoomモデル
class FocusRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    is_public = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<FocusRoom {self.name}>'
```
**注意**: データベース構造が変更されたため、一度`instance/db.sqlite`ファイルを削除して、データベースをリセットする必要があります。

---

## Step 2: バックエンド実装 (初期化とルーティング)

WebSocketサーバーを起動し、ルーム関連のURLとリアルタイム通信の処理を実装します。

### `app/__init__.py` の修正

`SocketIO`インスタンスを作成し、アプリケーションに組み込みます。

```python
# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO # ★追加

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO() # ★追加

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    socketio.init_app(app) # ★追加

    # ... 既存のコード ...
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    with app.app_context():
        db.create_all()

    return app
```

### `run.py` の修正

Flask標準のサーバーではなく、`socketio`を使ってアプリケーションを起動するように変更します。

```python
# run.py

from app import create_app, db, socketio # ★ socketioをインポート

app = create_app()

# with app.app_context():
#     db.create_all() # create_app()内で実行されるので不要な場合が多い

if __name__ == '__main__':
    # app.run(host='0.0.0.0',port=80,debug=True) # ★変更前
    socketio.run(app, host='0.0.0.0', port=80, debug=True) # ★変更後
```

### `app/routes.py` へのルートとイベントの追加

ルーム一覧、作成、入室のルートと、WebSocketイベントハンドラを追加します。

```python
# app/routes.py

# ... 既存のimport ...
from flask_socketio import join_room, leave_room, emit
from . import socketio
from .models import FocusRoom # ★追加

# ... 既存のルート ...

# ★ここから下を追記

@main.route('/rooms')
@login_required
def rooms():
    public_rooms = FocusRoom.query.filter_by(is_public=True).all()
    return render_template('rooms.html', rooms=public_rooms)

@main.route('/create_room', methods=['GET', 'POST'])
@login_required
def create_room():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_public = request.form.get('is_public') == 'on'
        
        new_room = FocusRoom(name=name, description=description, is_public=is_public, owner=current_user)
        db.session.add(new_room)
        # 作成者は自動的に参加者になる
        new_room.participants.append(current_user)
        db.session.commit()
        
        return redirect(url_for('main.room', room_id=new_room.id))
    return render_template('create_room.html')

@main.route('/room/<int:room_id>')
@login_required
def room(room_id):
    room = FocusRoom.query.get_or_404(room_id)
    # 参加者でなければ参加させるロジック（必要に応じて）
    if current_user not in room.participants:
        room.participants.append(current_user)
        db.session.commit()
    
    return render_template('room.html', room=room)

## --- SocketIO Events ---

@socketio.on('join')
def on_join(data):
    username = current_user.username
    room_id = data['room_id']
    join_room(room_id)
    emit('room_message', {'msg': username + ' has entered the room.'}, to=room_id)

@socketio.on('leave')
def on_leave(data):
    username = current_user.username
    room_id = data['room_id']
    leave_room(room_id)
    emit('room_message', {'msg': username + ' has left the room.'}, to=room_id)

@socketio.on('update_status')
def on_update_status(data):
    room_id = data['room_id']
    # 送信者以外のルームメンバーにブロードキャスト
    emit('status_updated', {
        'username': current_user.username,
        'status': data['status'],
        'gauge_level': data['gauge_level']
    }, to=room_id, include_self=False)

```

---

## Step 3: フロントエンド実装 (HTML & JavaScript)

ユーザーが操作する画面を作成します。

### `app/templates/rooms.html` (新規作成)

```html
{% extends "base.html" %}

{% block title %}フォーカスルーム一覧{% endblock %}

{% block content %}
<div class="card">
    <h2>フォーカスルーム一覧</h2>
    <a href="{{ url_for('main.create_room') }}" class="btn btn-primary mb-3">新しいルームを作成する</a>
    <ul class="list-group">
        {% for room in rooms %}
        <li class="list-group-item d-flex justify-content-between align-items-center">
            <div>
                <h5>{{ room.name }}</h5>
                <p class="mb-1">{{ room.description }}</p>
                <small>作成者: {{ room.owner.username }} | 参加者: {{ room.participants.count() }}人</small>
            </div>
            <a href="{{ url_for('main.room', room_id=room.id) }}" class="btn btn-secondary">入室する</a>
        </li>
        {% else %}
        <li class="list-group-item">現在、公開中のルームはありません。</li>
        {% endfor %}
    </ul>
</div>
{% endblock %}
```

### `app/templates/create_room.html` (新規作成)

```html
{% extends "base.html" %}

{% block title %}ルーム作成{% endblock %}

{% block content %}
<div class="card">
    <h2>新しいフォーカスルームを作成</h2>
    <form method="POST">
        <div class="form-group">
            <label for="name" class="form-label">ルーム名</label>
            <input type="text" name="name" id="name" class="form-control" required>
        </div>
        <div class="form-group">
            <label for="description" class="form-label">説明</label>
            <textarea name="description" id="description" class="form-control"></textarea>
        </div>
        <div class="form-group">
            <label class="checkbox-container">公開ルームにする
                <input type="checkbox" name="is_public" checked>
                <span class="checkmark"></span>
            </label>
        </div>
        <button type="submit" class="btn btn-primary">作成</button>
    </form>
</div>
{% endblock %}
```

### `app/templates/room.html` (新規作成)

```html
{% extends "base.html" %}

{% block title %}{{ room.name }}{% endblock %}

{% block content %}
<div class="card">
    <h2>{{ room.name }}</h2>
    <p>{{ room.description }}</p>
    <hr>
    <h4>参加者</h4>
    <div id="participants-list">
        {% for user in room.participants %}
        <div id="user-{{ user.username }}" class="participant-card">
            <strong>{{ user.username }}</strong>
            <p>ステータス: <span class="status">{{ user.status }}</span></p>
            <div class="progress">
                <div class="progress-bar" role="progressbar" style="width: {{ user.current_gauge_level }}%;" aria-valuenow="{{ user.current_gauge_level }}" aria-valuemin="0" aria-valuemax="100">
                    {{ user.current_gauge_level }}%
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
<div class="card mt-4">
    <h4>ルームメッセージ</h4>
    <div id="messages" style="height: 150px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px;"></div>
</div>

<!-- Socket.IOクライアントライブラリ -->
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const roomId = "{{ room.id }}";

    // サーバーに接続したらjoinイベントを送信
    socket.on('connect', () => {
        socket.emit('join', { room_id: roomId });
    });

    // サーバーからメッセージを受信
    socket.on('room_message', (data) => {
        const messages = document.getElementById('messages');
        messages.innerHTML += `<p>${data.msg}</p>`;
        messages.scrollTop = messages.scrollHeight;
    });

    // 他のユーザーのステータス更新を受信
    socket.on('status_updated', (data) => {
        const userCard = document.getElementById(`user-${data.username}`);
        if (userCard) {
            userCard.querySelector('.status').textContent = data.status;
            const progressBar = userCard.querySelector('.progress-bar');
            progressBar.style.width = `${data.gauge_level}%`;
            progressBar.textContent = `${data.gauge_level}%`;
            progressBar.setAttribute('aria-valuenow', data.gauge_level);
        }
    });

    // ウィンドウを閉じる時にleaveイベントを送信
    window.addEventListener('beforeunload', () => {
        socket.emit('leave', { room_id: roomId });
    });
});
</script>
{% endblock %}
```

---

## Step 4: 既存機能との連携

`focus.html`から、ルームにステータスを送信する仕組みは、より高度な実装（例：フォーカスモード開始時にどのルームに参加するか選択させるなど）が必要になります。

概念的な実装としては、`focus.html`のJavaScriptに、現在の`roomId`を何らかの形で（例：URLパラメータや`sessionStorage`経由で）渡し、`socket.io`の接続を確立します。そして、`tick`関数や`sendUserStatusUpdate`関数内で、`socket.emit('update_status', ...)`を呼び出すことで、ゲージ情報をルームに送信できます。

## まとめ

お疲れ様でした！このチュートリアルで実装したコードにより、FocusFlowにリアルタイムで他のユーザーの存在を感じられる「フォーカスルーム」が追加されました。

ここからさらに、UIを洗練させたり、ルーム内での「応援」機能を実装したりと、多くの可能性が広がっています。