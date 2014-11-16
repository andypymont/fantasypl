try:
	import simplejson as json
except ImportError:
	import json

import os

from app import app, db
from auth import current_user, load_user, login_manager, login_required
from datetime import datetime
from fantasypl import get_lineup, get_fixture_players, get_teams, next_opponents, current_gameweek, last_gameweek, next_gameweek, formation
from fantasypl import valid_formation, pagination, week_pagination, add_waiver_claim, waiver_status, do_week_scoring, undo_week_scoring
from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from functools import wraps
from math import ceil
from unidecode import unidecode

@app.template_filter('datetime_deadline')
def filter_datetime_deadline(dt):
	return dt.strftime('%a %d/%m/%Y %H:%M')

@app.template_filter('status_class')
def filter_status_class(status):
	return dict(success='success', failure='danger').get(status, 'default')

@app.template_filter('jsescape')
def filter_jsescapequotes(s):
    return s.replace("'", "\\u0027")

@app.template_filter('fixture_date')
def filter_fixture_date(fd):
	return datetime.strptime(fd, '%Y-%m-%dT%H:%M:%S').strftime('%d %b')

def scorer_only(func):
	@wraps(func)
	def decorated_function(*args, **kwargs):
		if current_user.is_scorer():
			return func(*args, **kwargs)
		else:
			return redirect(url_for('lineup'))
	return decorated_function

@app.route('/')
@app.route('/standings/')
def standings():
	return render_template('standings.html', activepage="standings", current_user=current_user, teams=get_teams(), latest_results=last_gameweek()['schedule'])

@app.route('/schedule/')
def schedule():
	gameweeks = db.get('gameweeks')
	cgw = current_gameweek()
	gw = int(request.args.get('week', cgw['week']))

	pagin = pagination(gw, len(gameweeks))
	gameweek = gameweeks[gw - 1]

	return render_template('schedule.html', activepage="schedule", gameweek=gameweek, pagination=pagin)

@app.route('/scoring/')
@login_required
@scorer_only
def scoring():
	gameweeks = sorted(db.get('gameweeks'), key=lambda gw: gw['week'])
	for gw in gameweeks:
		gw['deadline'] = datetime.strptime(gw['deadline'], '%Y-%m-%dT%H:%M:%S')
		gw['conclusion'] = datetime.strptime(gw['conclusion'], '%Y-%m-%dT%H:%M:%S')

	return render_template('scoring.html', activepage="scoring", gameweeks=gameweeks)

@app.route('/scoring/week/<int:weekno>/')
@login_required
@scorer_only
def scoreweek(weekno):
	gw = db.get('gameweeks', dict(week=weekno))

	if len(gw) == 0:
		flash("Gameweek %s not found" % weekno)
		return redirect(url_for('scoring'))
	else:
		gw = gw[0]
		if gw['scored']:
			flash("Scoring for gameweek %s is not open. Please re-open scoring for this week first." % weekno)
			return redirect(url_for('scoring'))
		else:
			return render_template('scoreweek.html', activepage="scoring", gameweek=gw)

@app.route('/scoring/week/<int:weekno>/close/')
@login_required
@scorer_only
def closeweek(weekno):
	gw = db.get('gameweeks', dict(week=weekno))
	if gw:
		do_week_scoring(gw[0])

	return redirect(url_for('scoring'))

@app.route('/scoring/week/<int:weekno>/open/')
@login_required
@scorer_only
def openweek(weekno):
	gw = db.get('gameweeks', dict(week=weekno))
	if gw:
		undo_week_scoring(gw[0])

	return redirect(url_for('scoring'))		

def goals_from_scorefixture_form(form, side, players):
	goals = []

	players = dict([(unicode(player['_id']), player) for player in players])

	scorers = [players.get(scorer) for scorer in form.getlist(side + 'scorer')]
	assists = [players.get(assist) for assist in form.getlist(side + 'assist')]

	for n, scorer in enumerate(scorers):
		goals.append(dict(scorer=scorer, assist=assists[n]))

	return goals

def lineup_from_scorefixture_form(form, side, players):
	lineup = []

	players = dict([(unicode(player['_id']), player) for player in players])

	ids = request.form.getlist(side + 'player')

	start = [(form.get('%sstart%s' % (side, x), 'off') == 'on') for x in xrange(1, 15)]
	finish = [(form.get('%sfinish%s' % (side, x), 'off') == 'on') for x in xrange(1, 15)]

	if ids:
		for (n, playerid) in enumerate(ids):
			if playerid != '':
				player = players[playerid]
				player.update(start=start[n], finish=finish[n])
				lineup.append(player)

	return sorted(lineup, key=lambda player: (-int(player['start']), dict(G=1, D=2, M=3, F=4)[player['position']], player['name']))

@app.route('/scoring/week/<int:weekno>/fixture/<int:fixtureno>/', methods=['GET', 'POST'])
@login_required
@scorer_only
def scorefixture(weekno, fixtureno):
	gw = db.get('gameweeks', dict(week=weekno))

	if len(gw) == 0:
		flash("Gameweek %s not found" % weekno)
		return redirect(url_for('scoring'))
	else:
		gw = gw[0]
		if gw['scored']:
			flash("Scoring for gameweek %s is not open. Please re-open scoring for this week first." % weekno)
			return redirect(url_for('scoring'))
		else:
			try:
				fixture = gw['fixtures'][fixtureno - 1]
			except IndexError:
				flash("Fixture %s not found in the week %s." % (fixtureno, weekno))
				return redirect(url_for('scoring'))

			if request.method == 'POST':
				players = get_fixture_players(fixture)
				homegoals = goals_from_scorefixture_form(request.form, 'home', players)
				awaygoals = goals_from_scorefixture_form(request.form, 'away', players)

				fixture.update(homelineup=lineup_from_scorefixture_form(request.form, 'home', players),
							   awaylineup=lineup_from_scorefixture_form(request.form, 'away', players),
							   homegoals=homegoals, homescore=len(homegoals), awaygoals=awaygoals, awayscore=len(awaygoals))
				db.save(gw)

			return render_template('scorefixture.html', activepage="scoring", gameweek=gw, fixture=fixture, weekno=weekno, fixtureno=fixtureno)		

@app.route('/lineup/')
@login_required
def lineup():
	if current_user:
		players = get_lineup(current_user.get_name())
	deadline = current_gameweek()['deadline']
	return render_template('lineup.html', players=players, activepage="lineup", current_user=current_user,
										  next_opponents=next_opponents(), deadline=deadline)

@app.route('/teams/<userid>/')
def team(userid):
	user = load_user(userid)

	if not user:
		abort(404)

	players = get_lineup(user.get_name())

	cgw = current_gameweek()
	claims = db.get('claims', {'user': userid})

	if cgw['waiver'] < datetime.now():
		recent_changes = sorted([claim for claim in claims if (claim['week'] == cgw['week'] and claim['status'] == 'success')],
								key=lambda claim: claim['priority'])

	else:
		recent_changes = sorted([claim for claim in claims if (claim['week'] == (cgw['week'] - 1) and claim['status'] == 'success')],
								key=lambda claim: claim['priority'])

	return render_template('team.html', players=players, activepage='team', user=user, next_opponents=next_opponents(),
										recent_changes=recent_changes)

@app.route('/lineup/submit/', methods=['POST'])
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
	view = request.args.get('view', 'own')

	if cgw['waiver'] < datetime.now():
		# we have passed the waiver deadline
		current_claims = []
		week = int(request.args.get('week', cgw['week']))
	else:
		current_claims = sorted([claim for claim in  db.get('claims', dict(user=current_user.get_id(), week=cgw['week']))],
								key=lambda claim: claim['priority'])
		week = int(request.args.get('week', cgw['week'] - 1))

	query = dict(week=week)
	if view == 'league':
		query.update(status='success')
	else: # view == 'own' or somehow still omitted at this point
		query.update(user=current_user.get_id())

	prev_claims = sorted(db.get('claims', query),
						 key=lambda claim: (claim.get('order', 100), claim['priority']))

	return render_template('waivers.html', activepage='waivers', current_claims=current_claims, prev_claims=prev_claims,
										   current_claim_count=len(current_claims), week_pagination=week_pagination(week),
										   waiver_deadline=cgw['waiver'], view=view)

@app.route('/waivers/update/', methods=['POST'])
@login_required
def update_waiver_order():
	try:
		priorities = [int(prio) for prio in request.form.get('priorities', '').split(',')]
	except ValueError:
		priorities = []

	cgw = current_gameweek()

	if datetime.now() >= cgw['waiver']:
		flash("The deadline for waivers this week has passed. You can no longer edit your claims.")

	else:

		current_claims = sorted(db.get('claims', dict(user=current_user.get_id(), week=cgw['week'])),
								key=lambda claim: claim['priority'])
		deleted_claims = []

		for (n, claim) in enumerate(current_claims):
			try:
				claim['priority'] = priorities.index(n + 1)
			except ValueError:
				deleted_claims.append(claim)

		db.save_all([claim for claim in current_claims if claim not in deleted_claims])
		for claim in deleted_claims:
			db.delete(claim)

	return redirect(url_for('waiver_claims'))

@app.route('/players/')
def players():
	query = unidecode(request.args.get('q', '').lower())
	def search(playername):
		return (query == '') or (query in playername)

	players = db.get('players', {'searchname': search, 'club': lambda x: x != ''})

	pages = int(ceil(len(players) / 10.0))
	page = int(request.args.get('p', 1))

	pagin = pagination(page, pages)

	players = players[((page - 1) * 10):(page * 10)]

	gw_now = current_gameweek()

	for player in players:
		player['waiver'] = waiver_status(player, gw_now['week'], gw_now['deadline'], gw_now['waiver'], next_gameweek()['waiver'])

	return render_template('players.html', activepage="players", pagination=pagin, players=players, query=query)

@app.route('/players/add/', methods=['POST'])
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
				drop['team'] = ''
				drop['startingxi'] = 0

				db.save_all((add, drop))
				add_waiver_claim(current_user.get_id(), current_user.get_name(), cw['week'], add, drop, 'success')

			elif waiver['type'] == 'waiver':
				add_waiver_claim(current_user.get_id(), current_user.get_name(), cw['week'], add, drop)

	return redirect(request.args.get('next', url_for('lineup')))

@app.route('/json/players/team/<teamid>/')
def json_team_players(teamid):
	query = request.args.get('q', '')
	team = db.get_by_id(teamid)

	players = sorted(db.get('players', {'team': team['name'], 'searchname': lambda sn: (query in sn)}),
					 key=lambda player: ({'G': 1, 'D': 2, 'M': 3, 'F': 4}[player['position']], player['name']))

	return jsonify({'players': [dict(id=player['_id'], text='%s %s' % (player['position'], player['name'])) for player in players]})

@app.route('/json/players/club/<clubid>/')
def json_club_players(clubid):
	query = request.args.get('q', '')
	club = db.get_by_id(clubid)

	players = sorted(db.get('players', {'club': club['name'], 'searchname': lambda sn: (query in sn)}),
					 key=lambda player: ({'G': 1, 'D': 2, 'M': 3, 'F': 4}[player['position']], player['name']))

	return jsonify({'players': [dict(id=player['_id'], text='%s %s' % (player['position'], player['name'])) for player in players]})

@app.route('/json/players/')
def json_player():
	player = db.get_by_id(request.args.get('id', 0))
	if player:
		player = dict(id=player['_id'], text='%s %s' % (player['position'], player['name']))
	else:
		player = dict(id='', text='')

	return jsonify(dict(players=[player]))

if __name__ == '__main__':
	app.run()