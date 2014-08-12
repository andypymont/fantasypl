from app import app, db
from flask import redirect, render_template, request, url_for
from flask.ext.login import current_user, LoginManager, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(object):

	def __init__(self, dbuser):
		self.dbuser = dbuser

	def is_authenticated(self):
		return True

	def is_active(self):
		return True

	def is_anonymous(self):
		return True

	def get_id(self):
		return self.dbuser['userid']

	def get_name(self):
		return self.dbuser['name']

	def get_auth_token(self):
		return self.dbuser['token']

	def check_password(self, password):
		return check_password_hash(self.dbuser['password'], password)

@login_manager.user_loader
def load_user(userid):
	try:
		dbuser = db.get('users', {'userid': userid})[0]
	except IndexError:
		return None

	return User(dbuser)

@app.route('/login/', methods=["GET", "POST"])
def login():
	if request.method == 'POST':
		username = request.form.get('username', '')
		password = request.form.get('password', '')

		user = load_user(username)
		if user and user.check_password(password):
			login_user(user)
			return redirect(url_for('lineup'))
	return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect(url_for('lineup'))
