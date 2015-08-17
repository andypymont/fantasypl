from datetime import datetime
from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from math import ceil
from unidecode import unidecode

from app import app, db
from auth import current_user, load_user, login_manager, login_required
from fantasypl import get_lineup, get_fixture_players, get_teams, next_opponents, current_gameweek, last_gameweek, next_gameweek, formation
from fantasypl import valid_formation, pagination, week_pagination, add_waiver_claim, waiver_status, do_week_scoring, undo_week_scoring
from fantasypl import decode_iso_datetime, sort_player, sort_player_lineup, sort_player_form, sort_player_score, waiver_gameweek
from functools import wraps

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
	return render_template('standings.html', activepage="standings", current_user=current_user, teams=get_teams(), lastweek=last_gameweek())

@app.route('/schedule/')
def schedule():
	gameweeks = db.get('gameweeks')
	cgw = current_gameweek()
	gw = int(request.args.get('week', cgw['week']))

	pagin = pagination(gw, len(gameweeks))
	gameweek = gameweeks[gw - 1]

	return render_template('schedule.html', activepage="schedule", gameweek=gameweek, pagination=pagin)

@app.route('/score/<int:weekno>/<int:fixtureno>/')
def viewscore(weekno, fixtureno):
	gw = db.get('gameweeks', dict(week=weekno))

	if len(gw) == 0:
		abort(404)
	else:
		gw = gw[0]
		if not gw.get('scored', False):
			abort(404)
		else:
			try:
				fixture = gw.get('schedule', [])[fixtureno - 1]
			except IndexError:
				abort(404)

			homelineup = sorted(gw.get('lineups', dict()).get(fixture.get('home', ''), []), key=sort_player)
			awaylineup = sorted(gw.get('lineups', dict()).get(fixture.get('away', ''), []), key=sort_player)

			return render_template('fixture.html', activepage='schedule', gameweek=gw, fixture=fixture, homelineup=homelineup, awaylineup=awaylineup)

@app.route('/scoring/')
@login_required
@scorer_only
def scoring():
	gameweeks = sorted(db.get('gameweeks'), key=lambda gw: gw['week'])
	for gw in gameweeks:
		gw['deadline'] = decode_iso_datetime(gw['deadline'])
		gw['conclusion'] = decode_iso_datetime(gw['conclusion'])

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

	return sorted(lineup, key=sort_player_lineup)

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
def waiver_claims():
	cgw = current_gameweek()
	wgw = waiver_gameweek()

	print 'cgw %s' % cgw['week']
	print 'wgw %s' % wgw['week']

	view = request.args.get('view', 'own')

	if current_user.get_id() is None:
		view = 'league'

	current_claims = sorted([claim for claim in  db.get('claims', dict(user=current_user.get_id(), week=wgw['week']))],
							key=lambda claim: claim['priority'])

	if cgw['week'] == wgw['week']:
		week = int(request.args.get('week', cgw['week'] - 1))
	else:
		week = int(request.args.get('week', cgw['week']))

	claimquery = dict(week=week)
	tradequery = dict(week=week)
	if view == 'league':
		claimquery.update(status='success')
	else: # view == 'own' or somehow still omitted at this point
		claimquery.update(user=current_user.get_id())

	prev_claims = sorted(db.get('claims', claimquery),
						 key=lambda claim: (claim.get('order', 100), claim['priority']))
	trades = db.get('trades', tradequery)
	if view != 'league':
		trades = [trade for trade in trades if current_user.get_id() in (trade['first']['userid'], trade['second']['userid'])]

	return render_template('waivers.html', activepage='waivers', current_claims=current_claims, prev_claims=prev_claims,
										   trades=trades, current_claim_count=len(current_claims),
										   week_pagination=week_pagination(week), waiver_deadline=wgw['waiver'], view=view)

@app.route('/waivers/update/', methods=['POST'])
@login_required
def update_waiver_order():
	try:
		priorities = [int(prio) for prio in request.form.get('priorities', '').split(',')]
	except ValueError:
		priorities = []

	wgw = waiver_gameweek()

	if datetime.now() >= wgw['waiver']:
		flash("The deadline for waivers this week has passed. You can no longer edit your claims.")

	else:
		current_claims = sorted(db.get('claims', dict(user=current_user.get_id(), week=wgw['week'])),
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
	query = unidecode(unicode(request.args.get('q', '').lower()))
	pos = request.args.get('p', '').upper()
	if pos not in ('G', 'D', 'M', 'F', ''):
		pos = ''

	sorttype = request.args.get('s', 'score').lower()
	if sorttype not in ('score', 'form'):
		sorttype = 'score'

	filt = request.args.get('f', 'all')
	if filt not in ('all', 'free'):
		filt = 'all'

	def search(playername):
		return (query == '') or (query in playername)

	def status(team):
		return (filt == 'all') or (team == '')

	sort = dict(score=sort_player_score,
				form=sort_player_form)[sorttype]

	players = sorted(db.get('players', {'position': lambda x: pos in x, 'searchname': search, 'club': lambda x: x != '', 'team': status}), key=sort)

	pages = int(ceil(len(players) / 15.0))
	page = int(request.args.get('pg', 1))

	pagin = pagination(page, pages)

	players = players[((page - 1) * 15):(page * 15)]

	gw_now = current_gameweek()

	for player in players:
		player['waiver'] = waiver_status(player, gw_now['week'], gw_now['deadline'], gw_now['waiver'], next_gameweek()['waiver'])

	return render_template('players.html', activepage="players", pagination=pagin, players=players, query=query, pos=pos, sorttype=sorttype, filt=filt)

@app.route('/players/add/', methods=['POST'])
@login_required
def add_player():
	add_id = request.form.get('add', 0)
	drop_id = request.form.get('drop', 0)

	if (add_id > 0 and drop_id > 0):
		add = db.get_by_id(add_id)
		drop = db.get_by_id(drop_id)

		cgw = current_gameweek()
		wgw = waiver_gameweek()

		waiver = waiver_status(add, cgw['week'], cgw['deadline'], cgw['waiver'], next_gameweek()['waiver'])

		if waiver['addable']:

			if waiver['type'] == 'free':
				add['team'] = current_user.get_name()
				drop['team'] = ''
				drop['startingxi'] = 0

				db.save_all((add, drop))
				add_waiver_claim(current_user.get_id(), current_user.get_name(), cgw['week'], add, drop, 'success')

			elif waiver['type'] == 'waiver':
				add_waiver_claim(current_user.get_id(), current_user.get_name(), wgw['week'], add, drop)

	return redirect(request.args.get('next', url_for('lineup')))

@app.route('/json/players/team/<teamid>/')
def json_team_players(teamid):
	query = request.args.get('q', '')
	team = db.get_by_id(teamid)

	players = sorted(db.get('players', {'team': team['name'], 'searchname': lambda sn: (query in sn)}),
					 key=sort_player)

	return jsonify({'players': [dict(id=player['_id'], text='%s %s' % (player['position'], player['name'])) for player in players]})

@app.route('/json/players/club/<clubid>/')
def json_club_players(clubid):
	query = request.args.get('q', '').lower()
	club = db.get_by_id(clubid)

	players = sorted(db.get('players', {'club': club['name'], 'searchname': lambda sn: (query in sn)}),
					 key=sort_player)

	return jsonify({'players': [dict(id=player['_id'], text='%s %s' % (player['position'], player['name'])) for player in players]})

@app.route('/json/players/')
def json_player():
	player = db.get_by_id(request.args.get('id', 0))
	if player:
		player = dict(id=player['_id'], text='%s %s' % (player['position'], player['name']))
	else:
		player = dict(id='', text='')

	return jsonify(dict(players=[player]))