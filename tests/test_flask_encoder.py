import datetime
import json
import math
from decimal import Decimal

from connexion.apps.flask_app import FlaskJSONEncoder


def test_json_encoder():
    s = json.dumps({1: 2}, cls=FlaskJSONEncoder)
    assert '{"1": 2}' == s

    s = json.dumps(datetime.date.today(), cls=FlaskJSONEncoder)
    assert len(s) == 12

    s = json.dumps(datetime.datetime.utcnow(), cls=FlaskJSONEncoder)
    assert s.endswith('Z"')

    s = json.dumps(Decimal(1.01), cls=FlaskJSONEncoder)
    assert s == '1.01'

    s = json.dumps(math.expm1(1e-10), cls=FlaskJSONEncoder)
    assert s == '1.00000000005e-10'


def test_json_encoder_datetime_with_timezone():

    class DummyTimezone(datetime.tzinfo):

        def utcoffset(self, dt):
            return datetime.timedelta(0)

        def dst(self, dt):
            return datetime.timedelta(0)

    s = json.dumps(datetime.datetime.now(DummyTimezone()), cls=FlaskJSONEncoder)
    assert s.endswith('+00:00"')
