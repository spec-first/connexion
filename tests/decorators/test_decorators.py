import flask
from connexion.decorators.decorator import ResponseContainer


def test_response_container_content_type():
    app = flask.Flask(__name__)
    response = flask.Response(response='test response', content_type='text/plain')
    container = ResponseContainer(mimetype='application/json', response=response)

    with app.app_context():
        headers = container.flask_response_object().headers

    content_types = [value for key, value in headers.items() if key == 'Content-Type']
    assert len(content_types) == 1
    assert content_types[0] == 'text/plain'
