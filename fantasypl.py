try:
	import simplejson as json
except ImportError:
	import json

import os

from app import app, db
from flask import abort, redirect, render_template, request, url_for
from auth import current_user, login_manager, login_required

app.config.update(dict(DEBUG=True,
					   SECRET_KEY='Development key'))

def get_lineup(team):
	return sorted(db.get('players', {'team': team}),
				  key=lambda player: ({'G': 1, 'D': 2, 'M': 3, 'F': 4}[player['position']], player['name']))

def next_opponents():
	return dict([(club['name'], club['nextopponent']) for club in db.get('clubs')])

@app.route('/')
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

		db.save_all(players, 'players')

		return redirect(url_for('lineup'))

if __name__ == '__main__':
	app.run()