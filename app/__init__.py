from flask import Flask
from flask_splachemy import SQLAchemy
from flask_login import LoginManager

db = SQLAchemy()
login_manager = LoginManager()

def create_app():
	app = Flask(__name__)
	app.config['SECRET_KEY'] = 'your_secret_key'
	app.config['SQLACHEMY_DATABASE_URI'] = 'sqlite:///db.splite'
	app.config['SQLACHEMY_TRACK_MODIFICATIONS'] = False

	db.init_app(app)
	login_manager.init_app(app)
	login_manager.login_view = 'main.login'

	from .models import User
	@login_manager.user_loader
	def load_user(user_id):
		return User.query.get(int(user_id))

	from .routes import main as main_blueprint
	app.register_blueprint(main_blueprint)

	with app.app_context():
		db.create_all()

	return app
