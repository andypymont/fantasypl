from app import app, db
from datetime import datetime

def get_lineup(team):
	return sorted(db.get('players', {'team': team}),
				  key=lambda player: ({'G': 1, 'D': 2, 'M': 3, 'F': 4}[player['position']], player['name']))

def get_teams(reverse=False):
	rv = sorted(db.get('users'),
				key=lambda user: (-user.get('points', 0), -user.get('score', 0), -user.get('tiebreak', 0), user.get('draftorder', 0)))
	if reverse:
		rv = reversed(rv)
	
	return list(rv)

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