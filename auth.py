from app import app, db
from flask import flash, redirect, render_template, request, url_for
from flask.ext.login import current_user, LoginManager, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

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

	def get_dbid(self):
		return self.dbuser['_id']

	def get_name(self):
		return self.dbuser['name']

	def get_auth_token(self):
		return self.dbuser['token']

	def get_waiver_claims(self):
		return self.dbuser.get('claims', [])

	def add_waiver_claim(self, week, add, drop, status=''):
		if not ('claims' in self.dbuser.keys()):
			self.dbuser['claims'] = []

		try:
			priority = max(claim['priority'] for claim in self.dbuser['claims'] if claim['week'] == week) + 1
		except ValueError:
			priority = 1

		claim = dict(week=week, add=add, drop=drop, status=status, priority=priority)
		existing = [(c['week'], c['add']['_id'], c['drop']['_id']) for c in self.dbuser['claims']]

		if not ((claim['week'], claim['add']['_id'], claim['drop']['_id']) in existing):
			self.dbuser['claims'].append(claim)

		db.save(self.dbuser)

	def update_claims(self, claims):
		self.dbuser['claims'] = claims
		db.save(self.dbuser)

	def check_password(self, password):
		return check_password_hash(self.dbuser['password'], password)

	def change_password(self, newpassword):
		self.dbuser['password'] = generate_password_hash(newpassword)
		db.save(self.dbuser)

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
		rememberme = request.form.get('rememberme', False)

		user = load_user(username)
		if user and user.check_password(password):
			login_user(user, remember=rememberme)
			return redirect(request.args.get('next', url_for('lineup')))
		else:
			flash('Username/password combination not recognised')
	return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect(url_for('standings'))

@app.route('/change-password/', methods=["GET", "POST"])
@login_required
def change_password():
	if request.method == 'POST':
		new_password = request.form.get('newpassword1', '')
		if not current_user.check_password(request.form.get('currentpassword', '')):
			flash('Your current password was entered incorrectly. Please check and try again.')	
		elif new_password != request.form.get('newpassword2', ''):
			flash('Password not changed: new passwords provided did not match.')
		elif len(new_password) < 8:
			flash('Password not changed: Please use a password at least 8 characters long.')
		else:
			current_user.change_password(new_password)
			return redirect(url_for('standings'))

	return render_template('changepassword.html')