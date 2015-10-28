import datetime
import json
import pytz

from connexion.decorators.produces import JSONEncoder

def test_json_encoder():
    s = json.dumps({1: 2}, cls=JSONEncoder)
    assert '{"1": 2}' == s

    s = json.dumps(datetime.date.today(), cls=JSONEncoder)
    assert len(s) == 12

    s = json.dumps(datetime.datetime.utcnow(), cls=JSONEncoder)
    assert s.endswith('Z"')


def test_json_encoder_datetime_with_timezone():
	s = json.dumps(datetime.datetime.now(pytz.utc), cls=JSONEncoder)
	assert s.endswith('+00:00"')
