# FocusFlow開発チュートリアル - SNS機能編

このチュートリアルでは、前回作成したFocusFlowのMVPに、ユーザー同士が繋がるための基本的なSNS機能を追加していきます。

## はじめに - 「静かなる交流」を目指して

FocusFlowが目指すのは、一般的なSNSとは一線を画す、**「静かなる交流」**の場です。いいねの数やフォロワー数を競うのではなく、互いのフォーカスを尊重し、静かに応援し合うことで生まれる穏やかな連帯感を大切にします。

このチュートリアルで実装するSNS機能は、その思想を実現するための第一歩です。具体的には、以下の機能を実装します。

*   **ユーザープロフィールページの作成**
*   **フォロー/アンフォロー機能**
*   **アクティビティフィードの実装**

これを終えると、ユーザーは他のユーザーをフォローし、そのユーザーのフォーカスセッションを自分のダッシュボードで確認できるようになります。

**前提条件:**
このチュートリアルは、「FocusFlow開発チュートリアル (Python & Flask版)」を完了していることを前提としています。

## 1. データベースモデルの強化

SNS機能の中核となるフォロー機能を実装するため、`app/models.py`の`User`モデルを強化し、多対多のリレーションシップを定義します。

`app/models.py`を以下のように更新してください。

```python
# app/models.py

from flask_login import UserMixin
from . import db
from werkzeug.security import generate_password_hash, check_password_hash

# フォロー関係を定義するための中間テーブル
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

    # Userモデル自身に対する多対多のリレーションシップを定義
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # フォロー/アンフォロー/状態確認のためのヘルパーメソッド
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    # フォローしているユーザーのセッションを取得するメソッド
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
**注意:** データベースの構造が変更されたため、一度データベースファイルをリセットする必要があります。プロジェクトルートにある`instance/db.sqlite`ファイルを削除してください。これにより、既存のユーザーやセッションのデータはすべて消去されます。

## 2. ルーティングの拡張

プロフィール表示、フォロー、アンフォローのためのルートを`app/routes.py`に追加します。また、ダッシュボードでフォロー中のユーザーの活動を表示できるよう、`dashboard`ルートを修正します。

```python
# app/routes.py (既存のコードに追加・修正)

# ... (既存のimport文) ...

# ... (login, register, logoutルートは変更なし) ...

@main.route('/dashboard')
@login_required
def dashboard():
    # 自分のセッションとフォロー中のユーザーのセッションを取得
    my_sessions = FocusSession.query.filter_by(user_id=current_user.id).order_by(FocusSession.timestamp.desc()).all()
    followed_sessions = current_user.followed_sessions().all()
    return render_template('dashboard.html', username=current_user.username, my_sessions=my_sessions, followed_sessions=followed_sessions)

# ... (start_sessionルートは変更なし) ...

# --- ここから下のルートを新たに追加 ---

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

## 3. テンプレートの作成と修正

ユーザープロフィール画面を新たに追加し、ダッシュボードを修正してアクティビティフィードを表示します。

### プロフィールページのテンプレート作成 (`app/templates/user.html`)
`app/templates/`ディレクトリに、`user.html`という名前で新しいファイルを作成します。

```html
{% extends "base.html" %}

{% block title %}{{ user.username }}のプロフィール{% endblock %}

{% block content %}
    <section class="card">
        <h2>{{ user.username }}</h2>
        <p>フォロー数: {{ user.followed.count() }} | フォロワー数: {{ user.followers.count() }}</p>

        {% if user.id != current_user.id %}
            {% if not current_user.is_following(user) %}
                <a href="{{ url_for('main.follow', username=user.username) }}" class="btn btn-primary">フォローする</a>
            {% else %}
                <a href="{{ url_for('main.unfollow', username=user.username) }}" class="btn btn-secondary">フォロー解除</a>
            {% endif %}
        {% endif %}
    </section>

    <section class="card">
        <h3>{{ user.username }}さんのフォーカス履歴</h3>
        <table class="table">
            <thead>
                <tr>
                    <th>タスク名</th>
                    <th>フォーカス時間（分）</th>
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
                    <td colspan="3">まだフォーカス履歴がありません。</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </section>
{% endblock %}
```

### ダッシュボードのテンプレート修正 (`app/templates/dashboard.html`)
`dashboard.html`にアクティビティフィードのセクションを追加します。

```html
<!-- dashboard.html の自分のフォーカス履歴セクションの下に追加 -->
<section class="card">
    <h3>アクティビティフィード（フォロー中のユーザー）</h3>
    <table class="table">
        <thead>
            <tr>
                <th>ユーザー</th>
                <th>タスク名</th>
                <th>フォーカス時間（分）</th>
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
</section>
```

## 4. デザインの適用

前回のチュートリアルでは簡単なスタイルを適用しましたが、より洗練されたUIを適用します。
`app/templates/base.html`の`<head>`タグ内を修正し、`style.css`を読み込むように変更します。

```html
<!-- app/templates/base.html -->
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- <style>タグを削除し、代わりにlinkタグでCSSを読み込む -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <title>{% block title %}FocusFlow{% endblock %}</title>
</head>
```
これにより、プロジェクトに同梱されているモダンなダークテーマが適用されます。

## 5. 動作確認

1.  **データベースのリセット:** `instance/db.sqlite` ファイルを削除します。
2.  **アプリケーションの起動:** `python run.py` を実行します。
3.  **動作確認:**
    *   ブラウザを2つ（またはプライベートウィンドウ）開いて、それぞれ別のアカウントでユーザー登録・ログインします。（例: user1, user2）
    *   user1で何回かフォーカスセッションを記録します。
    *   user2でログインし、ダッシュボードのアクティビティフィードにuser1の活動が表示されていないことを確認します。
    *   user2で、user1のプロフィールページにアクセスします。（URLを直接 `http://127.0.0.1:5000/user/user1` のように入力）
    *   「フォローする」ボタンをクリックします。
    *   user2のダッシュボードに戻ると、アクティビティフィードにuser1のフォーカスセッションが表示されているはずです。

## 6. まとめと今後の展望

このチュートリアルでは、FocusFlowに「静かなる交流」の基礎となるSNS機能を追加しました。これにより、アプリケーションは単なる個人ツールから、他者と緩やかにつながり、互いに刺激を受けられるコミュニティへと進化しました。

ここからさらに、`focusflow.md`にあるような高度な機能へと発展させていくことができます。

*   **応援 (Cheer)機能**: アクティビティフィードに、テキスト入力不要のシンプルな「応援」ボタンを設置。クリックすると、相手のフォーカスゲージにポジティブなエフェクトを与えるなど、フォーカスを妨げずに応援の気持ちを伝えられます。
*   **フォーカスゲージとの連携**: 将来的にフォーカスゲージが実装されたら、アクティビティフィードに各ユーザーのリアルタイムのフォーカス度（例: 色の変化）を表示し、より一体感のある体験を創出します。
*   **フォーカスルーム機能**: 「TOEIC学習部屋」「もくもく開発部屋」など、共通の目的を持つユーザーが集まり、互いのフォーカス状態を可視化しながら作業できるバーチャル空間を実装します。
*   **AIコーチングとの連携**: 蓄積されたデータから「あなたとAさんは週末の朝に最もフォーカスする傾向があります」といった分析を提示したり、互いに良い影響を与え合っている関係性を可視化したりします。

このチュートリアルが、あなたの開発の助けとなれば幸いです。