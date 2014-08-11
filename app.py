import os
from flask import Flask
from inception import Database

app = Flask(__name__)
db = Database(os.path.join('db', 'fantasypl.db'))