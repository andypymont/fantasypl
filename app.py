import os
from flask import Flask
from inception import Database

app = Flask(__name__)

try:
	from settings import settings
	app.config.update(settings)
except ImportError:
	pass
	
db = Database(app.config.get('DATABASE', ':memory:'))