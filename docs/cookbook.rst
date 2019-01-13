Connexion Cookbook
==================

This section aims to be a cookbook of possible solutions for specific
use cases of Connexion.

Custom type format
------------------

It is possible to define custom type formats that are going to be used
by the Connexion payload validation on request parameters and response
payloads of your API.

Let's say your API deals with Products and you want to define a field
`price_label` that has a "money" format value. You can create a format
checker function and register that to be used to validate values of
the "money" format.

Example of a possible schema of Product having an attribute with
"money" format that would be defined in your OpenAPI specification:

.. code-block:: yaml

    type: object
    properties:
      title:
        type: string
      price_label:
        type: string
        format: money


Then we create a format checker function for that type of value:

.. code-block:: python

    import re

    MONEY_RE = re.compile('^\$\s*\d+(\.\d\d)?')

    def is_money(val):
        if not isinstance(val, str):
            return True
        return MONEY_RE.match(val)

The format checker function is expected to return `True` when the
value matches the expected format and return `False` when it
doesn't. Also is important to verify if the type of the value you are
trying to validate is compatible with the format. In our example we
check if the `val` is of type "string" before performing any further
checking.

The final step to make it work is registering our `is_money` function
to the format "money" in json_schema library. For that, we can use the
draft4 format checker decorator.

.. code-block:: python

    from jsonschema import draft4_format_checker

    @draft4_format_checker.checks('money')
    def is_money(val):
        ...

This is all you need to have validation for that format in your
Connexion application. Keep in mind that the format checkers should be
defined and registered before you run your application server. A full
example can be found at
https://gist.github.com/rafaelcaricio/6e67286a522f747405a7299e6843cd93


CORS Support
------------

CORS_ (Cross-origin resource sharing) is not built into Connexion, but you can use the `flask-cors`_ library
to set CORS headers:

.. code-block:: python

    import connexion
    from flask_cors import CORS

    app = connexion.FlaskApp(__name__)
    app.add_api('swagger.yaml')

    # add CORS support
    CORS(app.app)

    app.run(port=8080)


.. _CORS: https://en.wikipedia.org/wiki/Cross-origin_resource_sharing
.. _flask-cors: https://flask-cors.readthedocs.io/


Logging
------------

You can customize logging accessing the `_flask-logger` directly
or configuring the logger via dictConfig. 
Remember that you should configure logging for your project as soon
as possible when the program starts or you'll get the default configuration.

.. code-block:: python

    import connexion
    from logging.config import dictConfig
    
    
    dictConfig({
        'version': 1,
        'handlers': {
            'syslog': {
            'class': 'logging.handlers.SysLogHandler'
            }
        },
        'root': {
           'handlers': ['syslog']
        }
    })
    app = connexion.FlaskApp(__name__)
    app.app.logger.warn("I configured the flask logger!")
    app.add_api('swagger.yaml')
    app.run(port=8080)


.. _flask-logger: http://flask.pocoo.org/docs/1.0/logging/
