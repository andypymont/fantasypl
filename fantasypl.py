from app import app, db
from datetime import datetime

def decode_iso_datetime(iso_datetime):
	return datetime.strptime(iso_datetime, '%Y-%m-%dT%H:%M:%S')

def sort_player(player):
	return (dict(G=1, D=2, M=3, F=4)[player['position']],
			player['name'])

def sort_player_lineup(player):
	return (-int(player['start']),
			dict(G=1, D=2, M=3, F=4)[player['position']],
			player['name'])

def sort_player_form(player):
	return (-sum([f for f in player['form']]),
			dict(G=1, D=2, M=3, F=4)[player['position']],
			player['name'])

def sort_player_score(player):
	return (-player.get('totalscore', 0),
			dict(G=1, D=2, M=3, F=4)[player['position']],
			player['name'])

def get_lineup(team):
	return sorted(db.get('players', {'team': team}),
				  key=sort_player)

def get_fixture_players(fixture):
	clubnames = (fixture['home']['name'], fixture['away']['name'])
	return sorted(db.get('players', {'club': lambda c: c in clubnames}),
				  key=sort_player)

def get_teams(reverse=False):
	rv = sorted(db.get('users'),
				key=lambda user: (-user.get('points', 0), -user.get('score', 0), -user.get('tiebreak', 0), user.get('draftorder', 0)))
	if reverse:
		rv = reversed(rv)
	
	return list(rv)

def next_opponents():
	return dict([(club['name'], club['nextopponent']) for club in db.get('clubs')])

def last_gameweek():
	rv = sorted(db.get('gameweeks', {'completed': True}), key=lambda gw: gw['week'])[-1]
	rv['deadline'] = decode_iso_datetime(rv['deadline'])
	rv['waiver'] = decode_iso_datetime(rv['waiver'])
	rv['conclusion'] = decode_iso_datetime(rv['conclusion'])
	return rv

def current_gameweek():
	rv = sorted(db.get('gameweeks', {'completed': False}), key=lambda gw: gw['week'])[0]
	rv['deadline'] = decode_iso_datetime(rv['deadline'])
	rv['waiver'] = decode_iso_datetime(rv['waiver'])
	rv['conclusion'] = decode_iso_datetime(rv['conclusion'])
	return rv

def next_gameweek():
	rv = sorted(db.get('gameweeks', {'completed': False}), key=lambda gw: gw['week'])[1]
	rv['deadline'] = decode_iso_datetime(rv['deadline'])
	rv['waiver'] = decode_iso_datetime(rv['waiver'])
	rv['conclusion'] = decode_iso_datetime(rv['conclusion'])
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

def week_pagination(current_page):
	return pagination(current_page, current_gameweek()['week'])

def add_waiver_claim(user, username, week, add, drop, status=''):
	claims = db.get('claims', dict(user=user, week=week))
	existing = [(c['add']['_id'], c['drop']['_id']) for c in claims]

	if not ((add['_id'], drop['_id']) in existing):

		try:
			priority = max(claim['priority'] for claim in claims) + 1
		except ValueError:
			priority = 1

		document = dict(user=user, username=username, week=week, priority=priority, add=add, drop=drop, status=status)
		db.save(document, collection='claims')

def waiver_status(player, current_week, current_lineup_deadline, current_waiver_deadline, next_waiver_deadline):
	last_on_team = player.get('onteam', 0)
 	
	if player['team'] != '':
		return dict(text=player['team'], addable=False, type='owned')
	elif last_on_team == current_week:
		return dict(text='Waivers (%s)' % next_waiver_deadline.strftime('%d %b'), addable=False, type='waiver')
	elif datetime.now() > current_lineup_deadline:
		return dict(text='Waivers (%s)' % next_waiver_deadline.strftime('%d %b'), addable=False, type='waiver')
	elif datetime.now() < current_waiver_deadline:
		return dict(text='Waivers (%s)' % current_waiver_deadline.strftime('%d %b'), addable=True, type='waiver')
	else:
		return dict(text='Free Agent', addable=True, type='free')

def do_week_scoring(gw):

	# 0. Helper function / DRY for the home and away sides later
	players = dict()
	def scoreplayer(player, teamgoals, cleansheet):
		start = 1 * player.get('start', False)
		finish = 1 * player.get('finish', False)
		goals = sum([1 for goal in teamgoals if goal['scorer'] and goal['scorer']['_id'] == player['_id']])
		assists = sum([1 for goal in teamgoals if goal['assist'] and goal['assist']['_id'] == player['_id']])
		cleansheet = 1 * cleansheet
		cleansheetpoints = dict(G=3, D=2, M=0, F=0)[player.get('position', 'F')]

		player.update(score=(start + finish + (3 * goals) + (2 * assists) + (cleansheet * cleansheetpoints)))
		players[player.get('_id', '')] = player

	# 1. Score the players in the PL fixture (homelineup/awaylineup)
	for fixture in gw.get('fixtures', []):
		for player in fixture.get('homelineup', []):
			scoreplayer(player, fixture.get('homegoals', []), len(fixture.get('awaygoals', [])) == 0)
		for player in fixture.get('awaylineup', []):
			scoreplayer(player, fixture.get('awaygoals', []), len(fixture.get('homegoals', [])) == 0)

	# 2. Copy scores to the players in the fantasy gameweek, total each team during the process
	scores = dict()
	for (teamname, lineup) in gw.get('lineups', dict()).iteritems():
		for player in lineup:
			player.update(players.get(player['_id'], dict()))
			scores[teamname] = scores.get(teamname, 0) + player.get('score', 0)

	# 3. Update the team score totals in the Fantasy fixtures
	for fixture in gw['schedule']:
		fixture['homescore'] = scores.get(fixture['home'], 0)
		fixture['awayscore'] = scores.get(fixture['away'], 0)

	# 4. Save the gameweek
	gw.update(scored=True)
	db.save(gw)

	# 5. Update the league table and player score totals
	update_league_table()
	update_player_scores()

def undo_week_scoring(gw):

	# Clear the scores in the fantasy gameweek
	for (teamname, lineup) in gw.get('lineups', dict()).iteritems():
		for player in lineup:
			player.update(score=0)
	for fixture in gw['schedule']:
		fixture['homescore'] = fixture['awayscore'] = 0

	gw.update(scored=False)
	db.save(gw)

	# Update the league table and player score totals
	update_league_table()
	update_player_scores()

def update_player_scores():
	players = dict([(p['_id'], p) for p in db.get('players')])

	gameweeks = db.get('gameweeks', dict(scored=True))
	recent = sorted(gw['week'] for gw in gameweeks)[-4:]

	for player in players.values():
		player.pop('totalscore', None)
		player['form'] = [0] * len(recent)

	for gw in gameweeks:
		for result in gw.get('fixtures', []):
			for player in (result.get('homelineup', []) + result.get('awaylineup', [])):
				dbplayer = players.get(player.get('_id', ''))
				if dbplayer:
					dbplayer.update(totalscore=(dbplayer.get('totalscore', 0) + player.get('score', 0)))
					try:
						dbplayer['form'][recent.index(gw['week'])] = player.get('score', 0)
					except ValueError:
						pass

	db.save_all(players.values())

def update_league_table():
	teams = db.get('users')

	results = []
	for gw in db.get('gameweeks', dict(scored=True)):
		for result in gw.get('schedule', []):
			homeresult = dict(team=result.get('home', ''), score=int(result.get('homescore', 0)))
			awayresult = dict(team=result.get('away', ''), score=int(result.get('awayscore', 0)))

			homeresult['win'] = awayresult['loss'] = 1 * (homeresult.get('score', 0) > awayresult.get('score', 0))
			awayresult['win'] = homeresult['loss'] = 1 * (awayresult.get('score', 0) > homeresult.get('score', 0))
			homeresult['draw'] = awayresult['draw'] = 1 * (homeresult.get('score', 0) == awayresult.get('score', 0))

			results.append(homeresult)
			results.append(awayresult)

	for team in teams:
		team['wins'] = sum([result.get('win', 0) for result in results if result.get('team', '') == team.get('name', '')])
		team['losses'] = sum([result.get('loss', 0) for result in results if result.get('team', '') == team.get('name', '')])
		team['draws'] = sum([result.get('draw', 0) for result in results if result.get('team', '') == team.get('name', '')])
		team['points'] = (team['wins'] * 2) + team['draws']
		team['score'] = sum([result.get('score', 0) for result in results if result.get('team', '') == team.get('name', '')])

	db.save_all(teams)