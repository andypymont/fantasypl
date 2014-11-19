from app import app, db
from auth import generate_password_hash
from datetime import datetime, timedelta
from flask.ext.script import Manager
from fantasypl import current_gameweek, get_teams
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

def new_player(name, position, club):
	return dict(name=name,
				position=position,
				club=club,
				team='',
				startingxi=0,
				searchname=unidecode(unicode(name.lower())))

def update_next_fixtures(fixtures):

    clubs = dict([(c['name'], c) for c in db.get('clubs')])

    for (home, away) in fixtures:
        clubs[home]['nextopponent'] = '%s (H)' % away
        clubs[away]['nextopponent'] = '%s (A)' % home

    db.save_all(clubs.values())

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

@manager.command
def record_lineups():
	cgw = current_gameweek()

	if (cgw['deadline'] < datetime.now()) and (not cgw['conclusion'] < datetime.now()):
		
		lineups = db.get('players', dict(startingxi='1'))
		teams = set(p['team'] for p in lineups)
		cgw['lineups'] = dict()
		for team in teams:
			cgw['lineups'][team] = [player for player in teams]

		cgw['deadline'] = cgw['deadline'].isoformat()
		cgw['waiver'] = cgw['waiver'].isoformat()
		db.save(cgw)

@manager.command
def process_waivers_early():
	cgw = current_gameweek()
	minute_ago = datetime.now() - timedelta(minutes=1)

	cgw['deadline'] = cgw['deadline'].isoformat()
	cgw['waiver'] = datetime(year=minute_ago.year, month=minute_ago.month, day=minute_ago.day, hour=minute_ago.hour,
							 minute=minute_ago.minute, second=0).isoformat()

	db.save(cgw)

	process_waivers()

@manager.command
def process_waivers():
	cgw = current_gameweek()

	if cgw['waiver'] < datetime.now() and not cgw.get('waivers_done', False):

		teams = get_teams(reverse=True)
		players = db.get('players')
		claims = db.get('claims', dict(week=cgw['week']))

		# mark all players currently on teams
		for player in players:
			if player['team'] != '':
				player['onteam'] = cgw['week']

		# convert player list to dictionary so we can look up by id
		players = dict([(player['_id'], player) for player in players])

		def next_claim(team):
			try:
				return sorted([claim for claim in claims if claim['user'] == team['userid'] and claim['status'] == ''],
							  key=lambda claim: claim['priority'])[0]

			except IndexError:
				return False

		# process waiver claims
		done = 0
		seq = 0
		while not done:
			done = 1 # until we find out otherwise!

			for team in teams:
				while True:
					claim = next_claim(team)
					if claim:
						done = 0

						# update status of target player from master player list:
						claim['add'] = players[claim['add']['_id']]
						claim['drop'] = players[claim['drop']['_id']]

						# process claim
						if claim['add']['team'] != '':
							claim['status'] = 'failure'
							claim['whynot'] = 'player added by %s' % claim['add']['team']
						elif claim['drop']['team'] != team['name']:
							claim['status'] = 'failure'
							claim['whynot'] = 'no longer have player to drop'
						else:
							claim['status'] = 'success'
							claim['add']['team'] = team['name']
							claim['add']['onteam'] = cgw['week']
							claim['drop']['team'] = ''
							claim['drop']['startingxi'] = 0

							claim['order'] = seq
							seq += 1

							# success, exit loop
							break

					else:
						# no more claims for this user, exit loop
						break

		# save changes
		cgw = db.get_by_id(cgw['_id'])
		cgw['waivers_done'] = True

		db.save_all(players.values() + teams + claims + [cgw])

if __name__ == '__main__':
	manager.run()