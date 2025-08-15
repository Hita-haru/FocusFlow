from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, FocusSession, FlowStateLog
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
    followed_users_ids = [user.id for user in current_user.followed]
    followed_flow_logs = FlowStateLog.query.filter(FlowStateLog.user_id.in_(followed_users_ids)).order_by(FlowStateLog.timestamp.desc()).all()
    return render_template('dashboard.html', username=current_user.username, my_sessions=my_sessions, followed_flow_logs=followed_flow_logs)

@main.route('/focus')
@login_required
def focus():
    task_name = request.args.get('task', '名称未設定のタスク')
    return render_template('focus.html', task_name=task_name, current_username=current_user.username)

@main.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    sessions = FocusSession.query.filter_by(user_id=user.id).order_by(FocusSession.timestamp.desc()).all()
    return render_template('user.html', user=user, sessions=sessions)

@main.route('/api/user_status/<username>')
@login_required
def api_user_status(username):
    user = User.query.filter_by(username=username).first_or_404()
    return jsonify({
        'status': user.status,
        'gauge_level': user.current_gauge_level
    })

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

@main.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.all()
    users.sort(key=lambda x: x.total_focus_time, reverse=True)
    try:
        user_rank = users.index(current_user) + 1
    except ValueError:
        user_rank = None
    return render_template('leaderboard.html', users=users, user_rank=user_rank)

@main.route('/log_session', methods=['POST'])
@login_required
def log_session():
	data = request.get_json()
	task_name = data.get('task_name')
	duration_minutes = data.get('duration_minutes')

	if not task_name or duration_minutes is None:
		return jsonify({'status': 'error', 'message': 'タスク名と時間が指定されていません。'}), 400

	if int(duration_minutes) <= 0:
		return jsonify({'status': 'success', 'message': '時間は記録されませんでした。'})

	new_session = FocusSession(
		task_name=task_name,
		duration_minutes=int(duration_minutes),
		author=current_user
		)
	db.session.add(new_session)
	db.session.commit()

	current_user.status = 'オフライン'
	current_user.current_gauge_level = 0
	db.session.commit()

	return jsonify({'status': 'success'})

@main.route('/update_user_status', methods=['POST'])
@login_required
def update_user_status():
    data = request.get_json()
    status = data.get('status')
    gauge_level = data.get('gauge_level')

    if status is None:
        return jsonify({'status': 'error', 'message': 'ステータスが指定されていません。'}), 400

    current_user.status = status
    if gauge_level is not None:
        current_user.current_gauge_level = int(gauge_level)
    db.session.commit()

    return jsonify({'status': 'success'})

@main.route('/flow_state_achieved', methods=['POST'])
@login_required
def flow_state_achieved():
    log = FlowStateLog(user_id=current_user.id)
    db.session.add(log)
    db.session.commit()
    return jsonify({'status': 'success'})