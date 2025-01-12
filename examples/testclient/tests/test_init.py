import json
from unittest.mock import Mock

import pytest
from connexion.lifecycle import ConnexionResponse
from hello import handle_error


@pytest.mark.asyncio
async def test_handle_error():
    # Mock the ConnexionRequest object
    mock_req = Mock()
    mock_req.url = "http://some/url"
    # call the function
    conn_resp: ConnexionResponse = await handle_error(mock_req, ValueError("Value"))
    assert 500 == conn_resp.status_code
    # check structure of response
    resp_dict = json.loads(conn_resp.body)
    assert "Error" == resp_dict["title"]
