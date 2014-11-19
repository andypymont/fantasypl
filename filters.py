from app import app
from datetime import datetime

@app.template_filter('datetime_deadline')
def filter_datetime_deadline(dt):
	return dt.strftime('%a %d/%m/%Y %H:%M')

@app.template_filter('status_class')
def filter_status_class(status):
	return dict(success='success', failure='danger').get(status, 'default')

@app.template_filter('score_class')
def filter_score_class(score):
	return {0: 'danger', 1: 'warning', 2: 'default', 3: 'default'}.get(score, 'success')

@app.template_filter('jsescape')
def filter_jsescapequotes(s):
    return s.replace("'", "\\u0027")

@app.template_filter('fixture_date')
def filter_fixture_date(fd):
	return datetime.strptime(fd, '%Y-%m-%dT%H:%M:%S').strftime('%d %b')