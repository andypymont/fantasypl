from flask import Flask
from inception import MySQLDatabase

app = Flask(__name__)

try:
	from settings import settings
	app.config.update(settings)
except ImportError:
	pass

hostaddress = app.config.get('DATABASE_HOSTADDRESS', '')
dbname = app.config.get('DATABASE_NAME', '')
username = app.config.get('DATABASE_USERNAME', '')
password = app.config.get('DATABASE_PASSWORD', '')

db = MySQLDatabase(hostaddress, dbname, username, password)

#db = Database(app.config.get('DATABASE', ':memory:'))