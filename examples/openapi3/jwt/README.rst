=======================
JWT Auth Example
=======================

Running:

.. code-block:: bash

    $ sudo pip3 install -r requirements.txt
    $ ./app.py

Now open your browser and go to http://localhost:8080/ui/ to see the Swagger UI.
Use endpoint **/auth** to generate JWT token, copy it, then click **Authorize** button and paste the token.
Now you can use endpoint **/secret** to check autentication.