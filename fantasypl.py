try:
	import simplejson as json
except ImportError:
	import json

import os

from app import app, db
from auth import current_user, login_manager, login_required
from flask import abort, flash, redirect, render_template, request, url_for
from math import ceil

def get_lineup(team):
	return sorted(db.get('players', {'team': team}),
				  key=lambda player: ({'G': 1, 'D': 2, 'M': 3, 'F': 4}[player['position']], player['name']))

def next_opponents():
	return dict([(club['name'], club['nextopponent']) for club in db.get('clubs')])

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
	pageset = range(max(current_page - before, 1), max(current_page + after, 6))

	return dict(pages=pageset,
				pagecount=pages,
				current=current_page,
				prev=(current_page > 1),
				next=(current_page < pages))

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
	return render_template('lineup.html', players=players, activepage="lineup", current_user=current_user,
										  next_opponents=next_opponents())

@app.route('/lineup/submit', methods=['POST'])
def lineup_submit():
	if not current_user:
		abort(401)
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

@app.route('/players/')
def players():
	query = request.args.get('q', '')
	def search(playername):
		return (query == '') or (query in playername)

	players = db.get('players', {'searchname': search})

	pages = int(ceil(len(players) / 10.0))
	page = int(request.args.get('p', 1))

	pagin = pagination(page, pages)

	players = players[((page - 1) * 10):(page * 10)]

	return render_template('players.html', activepage="players", pagination=pagin, players=players, query=query)

@app.route('/players/search/', methods=['POST'])
def search_players():
	return redirect(url_for('players', q=request.form.get('search', '')))

if __name__ == '__main__':
	app.run()