from connexion.datastructures import MediaTypeDict

from .abstract import (  # NOQA
    AbstractRequestBodyValidator,
    AbstractResponseBodyValidator,
)
from .form_data import FormDataValidator, MultiPartFormDataValidator
from .json import (
    DefaultsJSONRequestBodyValidator,  # NOQA
    JSONRequestBodyValidator,
    JSONResponseBodyValidator,
    TextResponseBodyValidator,
)
from .parameter import ParameterValidator

VALIDATOR_MAP = {
    "parameter": ParameterValidator,
    "body": MediaTypeDict(
        {
            "*/*json": JSONRequestBodyValidator,
            "application/x-www-form-urlencoded": FormDataValidator,
            "multipart/form-data": MultiPartFormDataValidator,
        }
    ),
    "response": MediaTypeDict(
        {
            "*/*json": JSONResponseBodyValidator,
            "text/plain": TextResponseBodyValidator,
        }
    ),
}
