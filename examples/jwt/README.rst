=======================
JWT Auth Example
=======================

.. note::

    jwt is not supported by swagger 2.0: https://swagger.io/docs/specification/2-0/authentication/

Running:

.. code-block:: bash

    $ pip install -r requirements.txt
    $ python app.py

Now open your browser and go to http://localhost:8080/ui/ to see the Swagger UI.
Use endpoint **/auth** to generate JWT token, copy it, then click **Authorize** button and paste the token.
Now you can use endpoint **/secret** to check authentication.