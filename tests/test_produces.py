import datetime
import json
import math

from decimal import Decimal

from connexion.decorators.produces import JSONEncoder


def test_json_encoder():
    s = json.dumps({1: 2}, cls=JSONEncoder)
    assert '{"1": 2}' == s

    s = json.dumps(datetime.date.today(), cls=JSONEncoder)
    assert len(s) == 12

    s = json.dumps(datetime.datetime.utcnow(), cls=JSONEncoder)
    assert s.endswith('Z"')

    s = json.dumps(Decimal(1.01), cls=JSONEncoder)
    assert s == '1.01'

    s = json.dumps(math.expm1(1e-10), cls=JSONEncoder)
    assert s == '1.00000000005e-10'


def test_json_encoder_datetime_with_timezone():

    class DummyTimezone(datetime.tzinfo):

        def utcoffset(self, dt):
            return datetime.timedelta(0)

        def dst(self, dt):
            return datetime.timedelta(0)

    s = json.dumps(datetime.datetime.now(DummyTimezone()), cls=JSONEncoder)
    assert s.endswith('+00:00"')
