try:
	import simplejson as json
except ImportError:
	import json

import os

from app import app, db
from auth import current_user, login_manager, login_required
from datetime import datetime
from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from math import ceil
from unidecode import unidecode

def get_lineup(team):
	return sorted(db.get('players', {'team': team}),
				  key=lambda player: ({'G': 1, 'D': 2, 'M': 3, 'F': 4}[player['position']], player['name']))

def next_opponents():
	return dict([(club['name'], club['nextopponent']) for club in db.get('clubs')])

def current_gameweek():
	rv = sorted(db.get('gameweeks', {'completed': False}), key=lambda gw: gw['week'])[0]
	rv['deadline'] = datetime.strptime(rv['deadline'], '%Y-%m-%dT%H:%M:%S')
	rv['waiver'] = datetime.strptime(rv['waiver'], '%Y-%m-%dT%H:%M:%S')
	return rv

def next_gameweek():
	rv = sorted(db.get('gameweeks', {'completed': False}), key=lambda gw: gw['week'])[1]
	rv['deadline'] = datetime.strptime(rv['deadline'], '%Y-%m-%dT%H:%M:%S')
	rv['waiver'] = datetime.strptime(rv['waiver'], '%Y-%m-%dT%H:%M:%S')
	return rv	

def formation(players):
	rv = dict()
	for player in players:
		count = rv.get(player['position'], 0) + 1
		rv[player['position']] = count
	return rv

def valid_formation(players):
	valid_formations = (dict(G=1, D=5, M=3, F=2),
						dict(G=1, D=5, M=4, F=1),
						dict(G=1, D=4, M=5, F=1),
						dict(G=1, D=4, M=4, F=2),
						dict(G=1, D=4, M=3, F=3),
						dict(G=1, D=3, M=5, F=2),
						dict(G=1, D=3, M=4, F=3))
	return formation(players) in valid_formations

def pagination(current_page, pages):
	after = min(pages - current_page, 2) + 1
	before = 5 - after
	while (current_page - before) < 1:
		after += 1
		before -= 1

	pageset = range(max(current_page - before, 1), min(current_page + after, pages + 1))

	return dict(pages=pageset,
				pagecount=pages,
				current=current_page,
				prev=(current_page > 1),
				next=(current_page < pages))

def waiver_status(player, current_week, current_lineup_deadline, current_waiver_deadline, next_waiver_deadline):
	waived = player.get('waived', 0)

	if player['team'] != '':
		return dict(text=player['team'], addable=False, type='owned')
	elif waived == current_week:
		return dict(text='Waivers (%s)' % next_waiver_deadline.strftime('%d %b'), addable=False, type='waiver')
	elif datetime.now() > current_lineup_deadline:
		return dict(text='Waivers (%s)' % next_waiver_deadline.strftime('%d %b'), addable=False, type='waiver')
	elif datetime.now() < current_waiver_deadline:
		return dict(text='Waivers (%s)' % current_waiver_deadline.strftime('%d %b'), addable=True, type='waiver')
	else:
		return dict(text='Free Agent', addable=True, type='free')

@app.template_filter('datetime_deadline')
def filter_datetime_deadline(dt):
	return dt.strftime('%a %d/%m/%Y %H:%M')

@app.route('/')
@app.route('/standings/')
def standings():
	teams = sorted(db.get('users'),
				   key=lambda user: (-user.get('points', 0), -user.get('score', 0), 
				   					 -user.get('tiebreak', 0), user.get('draftorder', 0)))
	return render_template('standings.html', activepage="standings", current_user=current_user, teams=teams)

@app.route('/lineup/')
@login_required
def lineup():
	if current_user:
		players = get_lineup(current_user.get_name())
	deadline = current_gameweek()['deadline']
	return render_template('lineup.html', players=players, activepage="lineup", current_user=current_user,
										  next_opponents=next_opponents(), deadline=deadline)

@app.route('/lineup/submit', methods=['POST'])
def lineup_submit():
	if not current_user:
		abort(401)
	else:
		deadline = current_gameweek()['deadline']

		if deadline < datetime.now():
			flash("This week's lineup deadline has passed. Your lineup changes have not been saved.")
		else:
			players = get_lineup(current_user.get_name())
			for player in players:
				if request.form.get('startercheck%s' % player['_id'], '') == 'on':
					player['startingxi'] = '1'
				else:
					player['startingxi'] = '0'

			if valid_formation(player for player in players if player['startingxi'] == '1'):
				db.save_all(players, 'players')
				flash('Lineup saved')
			else:
				flash('Lineup reverted as was not a valid formation (please use 1 G, 3-5 D, 3-5 M, 1-3 F)')

		return redirect(url_for('lineup'))

@app.route('/waivers/')
@login_required
def waiver_claims():
	cgw = current_gameweek()
	claims = current_user.get_waiver_claims()

	if cgw['waiver'] < datetime.now():
		# we have passed the waiver deadline
		current_claims = []
		prev_claims = sorted([claim for claim in claims if claim['week'] == cgw['week']],
							 key=lambda claim: claim['priority'])
	else:
		current_claims = sorted([claim for claim in claims if claim['week'] == cgw['week']],
								key=lambda claim: claim['priority'])
		prev_claims = sorted([claim for claim in claims if claim['week'] == (cgw['week'] - 1)],
							 key=lambda claim: claim['priority'])

	return render_template('waivers.html', activepage='waivers', current_claims=current_claims, prev_claims=prev_claims,
										   current_claim_count=len(current_claims), waiver_deadline=cgw['waiver'])

@app.route('/waivers/update', methods=['POST'])
@login_required
def update_waiver_order():
	try:
		priorities = [int(prio) for prio in request.form.get('priorities', '').split(',')]
	except ValueError:
		priorities = []

	cgw = current_gameweek()

	if datetime.now() >= cgw['waiver']:
		flash("The deadline for waivers this week has passed. You can no longer edit your claims.")

	elif priorities:
		current_claims = sorted([claim for claim in current_user.get_waiver_claims() if claim['week'] == cgw['week']],
							    key=lambda claim: claim['priority'])
		other_claims = [claim for claim in current_user.get_waiver_claims() if claim not in current_claims]

		for (n, claim) in enumerate(current_claims):
			claim['priority'] = priorities.index(n + 1)

		current_user.update_claims(other_claims + current_claims)

	return redirect(url_for('waiver_claims'))

@app.route('/waivers/cancel')
@login_required
def cancel_waiver_claim():
	try:
		delete = int(request.args.get('n', '0'))
	except ValueError:
		delete = 0

	cgw = current_gameweek()

	if datetime.now() >= cgw['waiver']:
		flash("The deadline for waivers this week has passed. You can no longer edit your claims.")
	elif delete:
		current_claims = sorted([claim for claim in current_user.get_waiver_claims() if claim['week'] == cgw['week']],
							    key=lambda claim: claim['priority'])
		keep_claims = [claim for claim in current_user.get_waiver_claims() if claim not in current_claims]

		for (n, claim) in enumerate(current_claims):
			if (n + 1) != delete:
				keep_claims.append(claim)

		current_user.update_claims(keep_claims)

	return redirect(url_for('waiver_claims'))

@app.route('/players/')
def players():
	query = unidecode(request.args.get('q', '').lower())
	def search(playername):
		return (query == '') or (query in playername)

	players = db.get('players', {'searchname': search})

	pages = int(ceil(len(players) / 10.0))
	page = int(request.args.get('p', 1))

	pagin = pagination(page, pages)

	players = players[((page - 1) * 10):(page * 10)]

	gw_now = current_gameweek()

	for player in players:
		player['waiver'] = waiver_status(player, gw_now['week'], gw_now['deadline'], gw_now['waiver'], next_gameweek()['waiver'])

	return render_template('players.html', activepage="players", pagination=pagin, players=players, query=query)

@app.route('/players/add', methods=['POST'])
@login_required
def add_player():
	add_id = request.form.get('add', 0)
	drop_id = request.form.get('drop', 0)

	if (add_id > 0 and drop_id > 0):
		add = db.get_by_id(add_id)
		drop = db.get_by_id(drop_id)

		cw = current_gameweek()
		waiver = waiver_status(add, cw['week'], cw['deadline'], cw['waiver'], next_gameweek()['waiver'])

		if waiver['addable']:

			if waiver['type'] == 'free':
				add['team'] = current_user.get_name()
				add['startingxi'] = 0
				drop['team'] = ''
				drop['waived'] = cw['week']

				db.save_all((add, drop))
				current_user.add_waiver_claim(cw['week'], add, drop, 'success')

			elif waiver['type'] == 'waiver':
				current_user.add_waiver_claim(cw['week'], add, drop)

	return redirect(request.args.get('next', url_for('lineup')))

@app.route('/json/players/<teamid>/')
def json_team_players(teamid):
	query = request.args.get('q', '')
	team = db.get_by_id(teamid)

	players = sorted(db.get('players', {'team': team['name'], 'searchname': lambda sn: (query in sn)}),
					 key=lambda player: ({'G': 1, 'D': 2, 'M': 3, 'F': 4}[player['position']], player['name']))

	return jsonify({'players': [dict(id=player['_id'], text='%s %s' % (player['position'], player['name'])) for player in players]})

if __name__ == '__main__':
	app.run()