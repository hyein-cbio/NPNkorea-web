import json

from npnkorea.lambda_handler import handler


def event(path, body=None, method="POST"):
    return {
        "version": "2.0",
        "rawPath": path,
        "requestContext": {"http": {"method": method}},
        "body": json.dumps(body) if body is not None else None,
    }


def test_health():
    response = handler(event("/health", method="GET"), None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "ok"}


def test_combined_convert_endpoint():
    response = handler(event("/convert", {"point": {"lon": 126.978422, "lat": 37.566742}}), None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "code": "다사 5393 5205",
        "cell_corner": {"lon": 126.97832537074162, "lat": 37.56666295072665},
    }


def test_to_npn():
    response = handler(event("/to-npn", {"points": [{"lon": 126.978422, "lat": 37.566742}]}), None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"results": ["다사 5393 5205"]}


def test_domain_error_is_422():
    response = handler(event("/to-npn", {"points": [{"lon": 140, "lat": 37}]}), None)
    assert response["statusCode"] == 422


def test_combined_convert_accepts_code():
    response = handler(event("/convert", {"code": "dasa53965207"}), None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["code"] == "다사 5396 5207"


def test_batch_size_is_limited():
    points = [{"lon": 126.978422, "lat": 37.566742}] * 1001
    response = handler(event("/to-npn", {"points": points}), None)
    assert response["statusCode"] == 413


def test_options_is_handled():
    response = handler(event("/to-npn", method="OPTIONS"), None)
    assert response["statusCode"] == 204
