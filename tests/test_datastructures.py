from connexion.datastructures import MediaTypeDict


def test_media_type_dict():
    d = MediaTypeDict(
        {
            "*/*": "*/*",
            "*/json": "*/json",
            "*/*json": "*/*json",
            "multipart/*": "multipart/*",
            "multipart/form-data": "multipart/form-data",
        }
    )

    assert d["application/json"] == "*/json"
    assert d["application/problem+json"] == "*/*json"
    assert d["application/x-www-form-urlencoded"] == "*/*"
    assert d["multipart/form-data"] == "multipart/form-data"
    assert d["multipart/byteranges"] == "multipart/*"

    # Test __contains__
    assert "application/json" in d
