try:
	import simplejson as json
except ImportError:
	import json

import os

from app import app, db
from flask import render_template, redirect, url_for
from auth import current_user, login_manager, login_required

app.config.update(dict(DEBUG=True,
					   SECRET_KEY='Development key'))

@app.route('/')
@app.route('/lineup/')
@login_required
def lineup():
	if current_user:
		players = sorted(db.get('players', {'team': current_user.get_name()}),
				     	 key=lambda player: ({'G': 1, 'D': 2, 'M': 3, 'F': 4}[player['position']], player['name']))
	return render_template('lineup.html', players=players, activepage="lineup")

@app.route('/lineup/submit', methods=['POST'])
def lineup_submit():
	return redirect(url_for('lineup'))

if __name__ == '__main__':
	app.run()