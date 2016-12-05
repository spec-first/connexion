========================
Custom Validator Example
========================

In this example we fill-in non-provided properties with their defaults.
Validator code is based on example from `python-jsonschema docs`_.

Running:

.. code-block:: bash

    $ ./enforcedefaults.py

Now open your browser and go to http://localhost:8080/v1/ui/ to see the Swagger
UI. If you send a ``POST`` request with empty body ``{}``, you should receive
echo with defaults filled-in.

.. _python-jsonschema docs: https://python-jsonschema.readthedocs.io/en/latest/faq/#why-doesn-t-my-schema-that-has-a-default-property-actually-set-the-default-on-my-instance
