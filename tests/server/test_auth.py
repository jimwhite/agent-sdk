"""Tests for authentication middleware."""


def test_health_check_no_auth(client):
    """Test that health check endpoint doesn't require auth."""
    response = client.get("/alive")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_protected_endpoint_no_auth(client):
    """Test that protected endpoints require auth."""
    response = client.get("/conversations")
    assert response.status_code == 401
    assert "MissingAuthorization" in response.json()["error"]


def test_protected_endpoint_invalid_format(client):
    """Test invalid authorization header format."""
    response = client.get(
        "/conversations", headers={"Authorization": "InvalidFormat token"}
    )
    assert response.status_code == 401
    assert "InvalidAuthorizationFormat" in response.json()["error"]


def test_protected_endpoint_invalid_key(client):
    """Test invalid master key."""
    response = client.get(
        "/conversations", headers={"Authorization": "Bearer invalid-key"}
    )
    assert response.status_code == 401
    assert "InvalidMasterKey" in response.json()["error"]


def test_protected_endpoint_valid_auth(client, auth_headers):
    """Test valid authentication."""
    response = client.get("/conversations", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_docs_no_auth(client):
    """Test that docs endpoint doesn't require auth."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_no_auth(client):
    """Test that OpenAPI endpoint doesn't require auth."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()
