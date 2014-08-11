import json
import os

from app import app, db
from flask import render_template

app.config.update(dict(DEBUG=True))

@app.route('/')
def index():
	with open(os.path.join('db', 'teams.json')) as f:
		players = json.loads(f.read())
	players = sorted([player for player in players if player['team'] == 'Laura'],
				     key=lambda player: ({'G': 1, 'D': 2, 'M': 3, 'F': 4}[player['position']], player['name']))
	return render_template('index.html', players=players)

if __name__ == '__main__':
	app.run()