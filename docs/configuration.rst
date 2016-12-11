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
dictionary and can be modifified just like any dictionary::

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
``SPECIFICATION_FILE``                    OpenAPI specification file path.
``SPECIFICATION_DIR``                     Directory to use as bases to look for
                                          OpenAPI specification files.
``HOST``                                  The host interface to bind on when server
                                          is running.
``PORT``                                  The port to listen to when server is
                                          running.
``DEBUG``                                 Whether to execute the application in
                                          debug mode.
``AUTHENTICATE_NOT_FOUND_URLS``           Whether to authenticate paths not defined
                                          in the API specification.
``VALIDATE_RESPONSES``                    Whether to validate the operation handler
                                          responses against the API specification
                                          or not.
``STRICT_PARAMETERS_VALIDATION``          Whether to allow or not additional
                                          parameters in querystring and formData
                                          than the defineds in the API
                                          specification.
``MAKE_SPEC_AVAILABLE``                   Whether to make available the OpenAPI
                                          sepecification under
                                          CONSOLE_UI_PATH/swagger.json path.
``CONSOLE_UI_AVAILABLE``                  Whether to make the OpenAPI console
                                          available under CONSOLE_UI_PATH config
                                          path. Notice that this overrides the
                                          MAKE_SPEC_AVAILABLE configuration since
                                          the specification is required to be
                                          available to show the console UI.
``CONSOLE_UI_PATH``                       Path to mount the OpenAPI console.
========================================= =========================================
