import json
import os

from app import app, db
from flask import render_template, redirect, url_for

app.config.update(dict(DEBUG=True))

@app.route('/lineup/')
def lineup():
	with open(os.path.join('db', 'teams.json')) as f:
		players = json.loads(f.read())
	players = sorted([player for player in players if player['team'] == 'Andy'],
				     key=lambda player: ({'G': 1, 'D': 2, 'M': 3, 'F': 4}[player['position']], player['name']))
	return render_template('lineup.html', players=players)

@app.route('/lineup/submit', methods=['POST'])
def lineup_submit():
	return redirect(url_for('lineup'))

if __name__ == '__main__':
	app.run()