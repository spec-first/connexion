import datetime
import json

from connexion.decorators.produces import JSONEncoder

def test_json_encoder():
    s = json.dumps({1: 2}, cls=JSONEncoder)
    assert '{"1": 2}' == s

    s = json.dumps(datetime.date.today(), cls=JSONEncoder)
    assert len(s) == 12

    s = json.dumps(datetime.datetime.utcnow(), cls=JSONEncoder)
    assert s.endswith('Z"')


def test_json_encoder_datetime_with_timezone():

	class DummyTimezone(datetime.tzinfo):
		def utcoffset(self, dt):
			return datetime.timedelta(0)
		def dst(self, dt):
			return datetime.timedelta(0)

	s = json.dumps(datetime.datetime.now(DummyTimezone()), cls=JSONEncoder)
	assert s.endswith('+00:00"')
