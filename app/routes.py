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
	sessions = FocusSession.query.filter_by(user_id=current_user.id).order_by(FocusSession.timestamp.desc()).all()
	return render_template('dashboard.html', username=current_user.username, sessions=sessions)

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
