def test_health_endpoint(test_client) -> None:
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_federation_status_endpoint(test_client, auth_headers) -> None:
    response = test_client.get("/federation/status", headers=auth_headers)
    assert response.status_code == 200
    assert "enabled" in response.json()


def test_protected_route_requires_auth(test_client) -> None:
    response = test_client.get("/federation/status")
    assert response.status_code == 401
