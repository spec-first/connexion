import six

from connexion.decorators.produces import NoContent
from connexion.utils import normalize_tuple

BODY_TYPES = (six.text_type, six.binary_type, dict, list)


def validate_operation_output(response):
    """Will validate the format returned by a handler."""
    if isinstance(response, BODY_TYPES) or response == NoContent:
        response = (response, )

    body, status, headers = normalize_tuple(response, 3)

    if body == NoContent:
        body = b""
    elif not isinstance(body, BODY_TYPES):
        raise ValueError(
            "first returned value has to be {}, got {}".format(
                BODY_TYPES, type(body)
            )
        )
    status = status or 200
    if headers is not None and not isinstance(headers, dict):
        raise ValueError(
            "Type of 3rd return value is dict, got {}".format(
                type(headers)
            )
        )
    return body, status, headers
