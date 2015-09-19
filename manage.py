from app import app, db
from auth import generate_password_hash
from datetime import datetime, timedelta
from flask.ext.script import Manager
from fantasypl import current_gameweek, get_teams, new_player, process_waivers_now
from fantasypl import update_next_fixtures as _update_next_fixtures, process_waivers as _process_waivers, record_lineups as _record_lineups
from inception import _contains
from unidecode import unidecode

import random
import string

import filters
import routes

manager = Manager(app)

def get_player(name):
	try:
		return db.get('players', {'searchname': _contains(unidecode(unicode(name.lower())))})[0]
	except IndexError:
		return None

@manager.command
def newuser(name, username, password, draftorder=0, token=None):
	"Create a new user"

	tokens = [user['token'] for user in db.get('users')]
	while (token is None) or (token in tokens):
		token = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in xrange(20))

	user = dict(userid=username, password=generate_password_hash(password), name=name, token=token,
				wins=0, draws=0, losses=0, points=0, score=0, draftorder=draftorder)
	db.save(user, 'users')

@manager.command
def complete_gameweeks():
	changedweeks = []
	for gw in db.get('gameweeks'):
		conclusion = datetime.strptime(gw['conclusion'], '%Y-%m-%dT%H:%M:%S')
		if (not gw.get('completed', False)) and conclusion < datetime.now():
			gw['completed'] = True
			changedweeks.append(gw)
	if changedweeks:
		db.save_all(changedweeks)
		update_next_fixtures()

@manager.command
def update_next_fixtures():
	_update_next_fixtures()

@manager.command
def record_lineups():
	_record_lineups()

@manager.command
def process_waivers_early():
	process_waivers_now()

@manager.command
def process_waivers():
	_process_waivers()

if __name__ == '__main__':
	manager.run()