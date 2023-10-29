Testing
=======

test_client
-----------

Connexion exposes a ``test_client`` which you can use to make requests against your
Connexion application during tests.

.. code-block:: python

    def test_homepage():
        app = ...  # Set up app
        kwarg = {...}
        with app.test_client(**kwargs) as client:
            response = client.get("/")
            assert response.status_code == 200


The passed in keywords used to create a `Starlette` ``TestClient`` which is then returned.

For more information, please check the `Starlette documentation`_.

.. _Starlette documentation: https://www.starlette.io/testclient/

TestContext
-----------

To have access to the :doc:`context` variables during tests, you can use the :class:`.TestContext`
provided by Connexion.

.. code-block:: python

    from unittest.mock import MagicMock

    from connexion.context import operation
    from connexion.testing import TestContext


    def get_method():
        """Function called within TestContext you can access the context variables here."""
        return operation.method

    def test():
        operation = MagicMock(name="operation")
        operation.method = "post"
        with TestContext(operation=operation):
            assert get_method() == "post

If you don't pass in a certain context variable, the `TestContext` will generate a dummy one.
