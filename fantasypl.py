from app import app, db
from flask import render_template

app.config.update(dict(DEBUG=True))

@app.route('/')
def index():
	return render_template('index.html')

if __name__ == '__main__':
	app.run()