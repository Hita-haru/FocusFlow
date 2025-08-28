from flask_login import UserMixin
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta, datetime

# 中間テーブルは、それを使用するクラスよりも前に定義する必要があります

# フォロー関係を定義するための中間テーブル
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

# ルーム参加者を定義するための中間テーブル
room_participants = db.Table('room_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('room_id', db.Integer, db.ForeignKey('focus_room.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128))
    sessions = db.relationship('FocusSession', backref='author', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)
    status = db.Column(db.String(50), default='オフライン')
    current_gauge_level = db.Column(db.Integer, default=0)

    # フォローしている/されている関係 (多対多)
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    # 作成したルーム (1対多)
    created_rooms = db.relationship('FocusRoom', backref='owner', lazy='dynamic')

    # 参加しているルーム (多対多)
    joined_rooms = db.relationship('FocusRoom', secondary='room_participants', lazy='dynamic',
                                   backref=db.backref('participants', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_sessions(self):
        return FocusSession.query.join(
            followers, (followers.c.followed_id == FocusSession.user_id)).filter(
                followers.c.follower_id == self.id).order_by(
                    FocusSession.timestamp.desc())

    @property
    def total_focus_time(self):
        return db.session.query(db.func.sum(FocusSession.duration_minutes)).filter(FocusSession.user_id == self.id).scalar() or 0

    def weekly_focus_time(self):
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week_dt = datetime.combine(start_of_week, datetime.min.time())
        return db.session.query(db.func.sum(FocusSession.duration_minutes)).filter(
            FocusSession.user_id == self.id,
            FocusSession.timestamp >= start_of_week_dt
        ).scalar() or 0


class FocusSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(200), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  #例: 'session_start', 'session_end', 'flow_state'
    details = db.Column(db.String(200), nullable=True) #例: タスク名や時間
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

class FocusRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    is_public = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def weekly_focus_time_avg(self):
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week_dt = datetime.combine(start_of_week, datetime.min.time())

        participants = self.participants.all()
        num_participants = len(participants)

        if num_participants == 0:
            return 0

        user_ids = [user.id for user in participants]

        total_focus_time = db.session.query(db.func.sum(FocusSession.duration_minutes)).filter(
            FocusSession.user_id.in_(user_ids),
            FocusSession.timestamp >= start_of_week_dt
        ).scalar() or 0
        
        return round(total_focus_time / num_participants, 1)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('focus_room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    room = db.relationship('FocusRoom', backref=db.backref('chat_messages', cascade="all, delete-orphan", lazy=True))
    user = db.relationship('User', backref='chat_messages')
