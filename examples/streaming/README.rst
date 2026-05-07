=============================
Streaming Server-Sent Events
=============================

Preparing
---------

Create a new virtual environment and install the required libraries
with these commands:

.. code-block:: bash

    $ python -m venv my-venv
    $ source my-venv/bin/activate
    $ pip install 'connexion[swagger-ui,uvicorn]>=3.1.0'

Running
-------

Launch the connexion server with this command:

.. code-block:: bash

    $ python streaming.py

Watching the stream
-------------------

Visit http://localhost:8080/openapi/ui/ to explore the OpenAPI docs,
or watch the events arrive in real time with:

.. code-block:: bash

    $ curl -N http://localhost:8080/stream

You should see a tick event once per second.
