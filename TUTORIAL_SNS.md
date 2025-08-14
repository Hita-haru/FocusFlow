# FocusFlow開発チュートリアル - SNS機能編

このチュートリアルでは、前回作成したFocusFlowのMVPに、ユーザー同士が繋がるための基本的なSNS機能を追加していきます。具体的には、以下の機能を実装します。

*   **ユーザープロフィールページの作成**
*   **フォロー/アンフォロー機能**
*   **アクティビティフィードの実装**

このチュートリアルを終えると、ユーザーは他のユーザーをフォローし、そのユーザーの集中セッションを自分のダッシュボードで確認できるようになります。

**前提条件:**
このチュートリアルは、「FocusFlow開発チュートリアル (Python & Flask版)」を完了していることを前提としています。

## 1. データベースモデルの確認 (フォロー機能)

前回のチュートリアルで、既に`app/models.py`にフォロー機能のためのモデル定義が追加されています。ここでは、その内容を改めて確認します。

`app/models.py`は以下のようになっているはずです。

```python
# app/models.py

from flask_login import UserMixin
from . import db
from werkzeug.security import generate_password_hash, check_password_hash

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128))
    sessions = db.relationship('FocusSession', backref='author', lazy=True)

    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

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


class FocusSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(200), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

```

データベースの構造に変更があった場合は、一度データベースを再作成する必要があります。既存の`instance/db.sqlite`ファイルを削除してから、アプリケーションを再起動してください。
**注意: これまでのユーザーやセッションのデータはすべて消えてしまいます。**

## 2. プロフィールページとフォローボタンの作成

次に、各ユーザーのプロフィールページを作成し、他のユーザーがそのページからフォロー/アンフォローできるようにします。

### ルーティングの追加と修正 (`app/routes.py`)

`app/routes.py`に、プロフィール表示、フォロー、アンフォローのためのルートを追加し、`dashboard`ルートを修正します。

```python
# app/routes.py

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, FocusSession
from . import db

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return redirect(url_for('main.dashboard'))

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('このメールアドレスは既に使用されています。')
            return redirect(url_for('main.register'))

        new_user = User(email=email, username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('main.dashboard'))
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('メールアドレスまたはパスワードが正しくありません。')
            return redirect(url_for('main.login'))

        login_user(user, remember=remember)
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/dashboard')
@login_required
def dashboard():
    my_sessions = FocusSession.query.filter_by(user_id=current_user.id).order_by(FocusSession.timestamp.desc()).all()
    followed_sessions = current_user.followed_sessions().all()
    return render_template('dashboard.html', username=current_user.username, my_sessions=my_sessions, followed_sessions=followed_sessions)

@main.route('/start_session', methods=['POST'])
@login_required
def start_session():
    task_name = request.form.get('task_name')
    duration_minutes = request.form.get('duration_minutes')

    if not task_name or not duration_minutes:
        flash('タスク名と時間を入力してください。')
        return redirect(url_for('main.dashboard'))

    new_session = FocusSession(
        task_name=task_name,
        duration_minutes=int(duration_minutes),
        author=current_user
        )
    db.session.add(new_session)
    db.session.commit()

    return redirect(url_for('main.dashboard'))

@main.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    sessions = user.sessions.order_by(FocusSession.timestamp.desc()).all()
    return render_template('user.html', user=user, sessions=sessions)

@main.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('自分自身をフォローすることはできません。')
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(f'{user.username}さんをフォローしました。')
    return redirect(url_for('main.user', username=username))

@main.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('自分自身をアンフォローすることはできません。')
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(f'{user.username}さんのフォローを解除しました。')
    return redirect(url_for('main.user', username=username))
```

### プロフィールページのテンプレート作成 (`app/templates/user.html`)

`app/templates/`ディレクトリに、`user.html`という名前で新しいファイルを作成します。

```html
{% extends "base.html" %}

{% block title %}{{ user.username }}のプロフィール{% endblock %}

{% block content %}
    <h2>{{ user.username }}</h2>
    <p>フォロー数: {{ user.followed.count() }} | フォロワー数: {{ user.followers.count() }}</p>

    {% if user.id != current_user.id %}
        {% if not current_user.is_following(user) %}
            <a href="{{ url_for('main.follow', username=user.username) }}">フォローする</a>
        {% else %}
            <a href="{{ url_for('main.unfollow', username=user.username) }}">フォロー解除</a>
        {% endif %}
    {% endif %}

    <hr>

    <h3>{{ user.username }}さんの集中履歴</h3>
    <table border="1">
        <thead>
            <tr>
                <th>タスク名</th>
                <th>集中時間（分）</th>
                <th>日時</th>
            </tr>
        </thead>
        <tbody>
            {% for session in sessions %}
            <tr>
                <td>{{ session.task_name }}</td>
                <td>{{ session.duration_minutes }}</td>
                <td>{{ session.timestamp.strftime('%Y-%m-%d %H:%M') }}</td>
            </tr>
            {% else %}
            <tr>
                <td colspan="3">まだ集中履歴がありません。</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
{% endblock %}
```

### ダッシュボードのテンプレート修正 (`app/templates/dashboard.html`)

`app/templates/dashboard.html`を修正して、アクティビティフィードを表示し、ユーザー名にリンクをつけます。

```html
{% extends "base.html" %}

{% block title %}ダッシュボード{% endblock %}

{% block content %}
    <h2>ようこそ, {{ username }} さん!</h2>

    <h3>新しい集中セッションを開始</h3>
    <form method="POST" action="/start_session">
        <p><input type="text" name="task_name" placeholder="タスク名" required></p>
        <p><input type="number" name="duration_minutes" placeholder="集中時間（分）" required></p>
        <p><button type="submit">開始</button></p>
    </form>

    <h3>自分の集中履歴</h3>
    <table border="1">
        <thead>
            <tr>
                <th>タスク名</th>
                <th>集中時間（分）</th>
                <th>日時</th>
            </tr>
        </thead>
        <tbody>
            {% for session in my_sessions %}
            <tr>
                <td>{{ session.task_name }}</td>
                <td>{{ session.duration_minutes }}</td>
                <td>{{ session.timestamp.strftime('%Y-%m-%d %H:%M') }}</td>
            </tr>
            {% else %}
            <tr>
                <td colspan="3">まだ集中履歴がありません。</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <hr>

    <h3>アクティビティフィード（フォロー中のユーザー）</h3>
    <table border="1">
        <thead>
            <tr>
                <th>ユーザー</th>
                <th>タスク名</th>
                <th>集中時間（分）</th>
                <th>日時</th>
            </tr>
        </thead>
        <tbody>
            {% for session in followed_sessions %}
            <tr>
                <td><a href="{{ url_for('main.user', username=session.author.username) }}">{{ session.author.username }}</a></td>
                <td>{{ session.task_name }}</td>
                <td>{{ session.duration_minutes }}</td>
                <td>{{ session.timestamp.strftime('%Y-%m-%d %H:%M') }}</td>
            </tr>
            {% else %}
            <tr>
                <td colspan="4">フォローしているユーザーの活動はまだありません。</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
{% endblock %}
```

## 3. アプリケーションの実行と動作確認

1.  **データベースのリセット:** `instance/db.sqlite` ファイルを削除します。
2.  **アプリケーションの起動:** `python run.py` を実行します。
3.  **動作確認:**
    *   ブラウザを2つ（またはプライベートウィンドウ）開いて、それぞれ別のアカウントでユーザー登録・ログインします。（例: user1, user2）
    *   user1で何回か集中セッションを記録します。
    *   user2でログインし、ダッシュボードのアクティビティフィードにuser1の活動が表示されていないことを確認します。
    *   user2で、user1のプロフィールページにアクセスします。（URLを直接 `http://127.0.0.1:5000/user/user1` のように入力）
    *   「フォローする」リンクをクリックします。
    *   user2のダッシュボードに戻ると、アクティビティフィードにuser1の集中セッションが表示されているはずです。
    *   user1のプロフィールページで、フォロワー数が1になっていることを確認します。
    *   「フォロー解除」を試し、フィードから履歴が消えることも確認してみてください。

## 4. まとめと今後の展望

このチュートリアルでは、FocusFlowに基本的なSNS機能を追加しました。これにより、単なる個人の集中記録ツールから、他者と緩やかにつながり、互いに刺激を受けられるコミュニティアプリケーションへの第一歩を踏み出しました。

ここからさらに、`focusflow.md`にあるような高度な機能へと発展させていくことができます。

*   **応援 (Cheer)機能**: アクティビティフィードに「応援」ボタンを追加し、クリックすると相手に通知がいく（ただし集中を妨げない方法で）。
*   **集中ルーム**: 複数のユーザーが同じ目的で集まり、互いの集中状態を（匿名化して）可視化しながら作業する機能。
*   **リアルタイム性の向上**: WebSocketを導入し、フォローしているユーザーが集中を開始したらリアルタイムでフィードが更新されるようにする。

このチュートリアルが、あなたの開発の助けとなれば幸いです。