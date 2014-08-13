import sqlite3

try:
	import simplejson as json
except ImportError:
	import json

def inception_factory(cursor, row):
	rv = json.loads(row[2])
	rv.update(_id=unicode(row[0]),
			  _collection=unicode(row[1]))
	return rv

def filter_results(results, filters):
	def filter_result(result, filters):
		for (field, flter) in filters.iteritems():
			if callable(flter):
				if not flter(result.get(field, '')):
					return False
			else:
				if not (result.get(field, '') == flter):
					return False
		return True
	return [result for result in results if filter_result(result, filters)]

class Database():

	def __init__(self, path, app=None):
		self.dbpath = path
		self.app = app
		if app:
			from flask import g
			self.__dbclose = app.teardown_appcontext(self.__dbclose)

	def __dbconnect(self):
		rv = sqlite3.connect(self.dbpath, detect_types=sqlite3.PARSE_DECLTYPES)
		rv.row_factory = inception_factory
		return rv

	def __dbget(self):
		if self.app:
			if not hasattr(g, 'inception_sqlite_db'):
				g.inception_sqlite_db = self.__dbconnect()
			return g.inception_sqlite_db
		else:
			return self.__dbconnect()

	def __dbclose(self):
		if self.app:
			if hasattr(g, 'inception_sqlite_db'):
				g.inception_sqlite_db.close()

	def __dbinit(self):
		db = self.__dbget()
		db.execute('drop table if exists inception;')
		db.execute('create table inception (id integer primary key autoincrement, collection text not null, document text);')
		db.commit()

	def get_by_id(self, id):
		db = self.__dbget()
		return db.execute('select * from inception where id = ?', (id,)).fetchone()

	def get(self, collection=None, query=None):
		db = self.__dbget()
		
		if collection:
			sql, params = 'select * from inception where collection = ?', (collection,)
		else:
			sql, params = 'select * from inception', ()

		results = db.execute(sql, params).fetchall()
		if query:
			results = filter_results(results, query)

		return results

	def save(self, document, collection=None):
		collection = document.get('_collection', None) or collection
		if not collection:
			collection = ''

		docid = document.pop('_id', None)
		if docid:
			sql, params = ('insert or replace into inception (id, collection, document) values (?, ?, ?)',
						   (int(docid), collection, json.dumps(document)))
		else:
			sql, params = ('insert or replace into inception (collection, document) values (?, ?)',
						   (collection, json.dumps(document)))

		db = self.__dbget()
		db.execute(sql, params)
		db.commit()

	def save_all(self, documents, collection=None):
		db = self.__dbget()
		
		for document in documents:
			collection = document.get('_collection', None) or collection
			if not collection:
				collection = ''

			docid = document.pop('_id', None)
			if docid:
				sql, params = ('insert or replace into inception (id, collection, document) values (?, ?, ?)',
						   (docid, collection, json.dumps(document)))
			else:
				sql, params = ('insert or replace into inception (collection, document) values (?, ?)',
							   (collection, json.dumps(document)))
			db.execute(sql, params)

		db.commit()