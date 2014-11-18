try:
	import simplejson as json
except ImportError:
	import json

import filters
import routes

from app import app, db

if __name__ == '__main__':
	app.run()