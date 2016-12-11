Configuration Handling
======================

.. versionadded:: 1.0.130

Connexion supports a series of configurations that define how the
application should run or behave.

The way configuration in Connexion is designed tries to be fiel to how
Flask configurations work. We levarage the Flask support to
configurations adding the possibility to use configuration file or
environment variables for Connexion specific settings. That way we
enable you to use Connexion in conjunction with other
extensions. Futhermore, the development cycle of Connexion
applications is as close as possible to using Flask direcly.


Configuration Basics
====================

We provide the `connexion.App.config` which is a subclass of a
dictionary and can be modifified just like any dictionary:

.. code-block:: python

    app = connexion.App(__name__)
    app.config['SPECIFICATION_FILE'] = './swagger.yaml'


The configurations are also possible to come from environment
variables. The lookup order of configurations is:

- Set directly in the ``connexion.App#config`` configuration
  attribute;
- Set while calling ``connexion.App`` or ``connexion.App.add_api``
  directly;
- Included in a configuration file passed to ``connexion.App`` or
  ``connexion.App.add_api``;
- An environment variable with same name of the configuration setting;


Builtin Configuration Values
----------------------------

The following configuration values are used internally by Connexion:

.. tabularcolumns:: |p{6.5cm}|p{8.5cm}|

========================================= =========================================
``SPECIFICATION_FILE``                    OpenAPI specification file path. Defaults
                                          to: None
``SPECIFICATION_DIR``                     Directory to use as bases to look for
                                          OpenAPI specification files. Defaults to:
                                          ""
``HOST``                                  The host interface to bind on when server
                                          is running. Defaults to: "0.0.0.0"
``PORT``                                  The port to listen to when server is
                                          running. Defaults to: 5000
``WSGI_SERVER_CONTAINER``                 Which WSGI server container to use.
                                          Options are: "flask", "gevent", and
                                          "tornado". Defaults to: "flask"
``DEBUG``                                 Whether to execute the application in
                                          debug mode. Defaults to: False
``AUTHENTICATE_NOT_FOUND_URLS``           Whether to authenticate paths not defined
                                          in the API specification. Defaults to:
                                          False
``VALIDATE_RESPONSES``                    Whether to validate the operation handler
                                          responses against the API specification
                                          or not. Defaults to: False
``STRICT_PARAMETERS_VALIDATION``          Whether to allow or not additional
                                          parameters in querystring and formData
                                          than the defineds in the API
                                          specification. Defaults to: False
``MAKE_SPEC_AVAILABLE``                   Whether to make available the OpenAPI
                                          sepecification under
                                          CONSOLE_UI_PATH/swagger.json path.
                                          Defaults to: True
``JSON_ENCODER``                          Defines which encoder to use when
                                          serializing objects to JSON. Defaults to:
                                          "connexion.decorators.produces.JSONEncode
                                          r"
``STUB_NOT_IMPLEMENTED_ENDPOINTS``        Returns status code 501, and "Not
                                          Implemented Yet" payload, for the
                                          endpoints which handlers are not found.
                                          Defaults to: False
``MOCK_API``                              Returns example data for all endpoints or
                                          for which handlers are not found. Options
                                          are: None, "all" or "notimplemented".
                                          Defaults to: None
``CONSOLE_UI_AVAILABLE``                  Whether to make the OpenAPI console
                                          available under CONSOLE_UI_PATH config
                                          path. Notice that this overrides the
                                          MAKE_SPEC_AVAILABLE configuration since
                                          the specification is required to be
                                          available to show the console UI.
                                          Defaults to: True
``CONSOLE_UI_PATH``                       Path to mount the OpenAPI console.
                                          Defaults to: "/ui"
========================================= =========================================


Using Environment Variables for Configurations
----------------------------------------------

Connexion automatically look for configurations in the environment
variables of the running system. For that you have to set the
environment variable in the format ``CONNEXION_{{CONFIG_NAME}}``. For
example, to set the port that Connexion should use to run the
application you should set the environment variable
``CONNEXION_PORT`` to 8080.

.. code-block:: bash

    $ export CONNEXION_PORT=8080
    $ connexion run swagger.yaml -v
    INFO:werkzeug: * Running on http://0.0.0.0:8080/ (Press CTRL+C to quit)


Using File for Configurations
-----------------------------

You can generate a base configuration file using the Connexion CLI:

.. code-block:: bash

    $ connexion default-config > myapp.conf
