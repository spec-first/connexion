
def canonical_base_url(base_path):
    """
    Make given "basePath" a canonical base URL which can be prepended to paths starting with "/".
    """
    return base_path.rstrip('/')

from .abstract import AbstractApi
from .flask_api import FlaskApi
