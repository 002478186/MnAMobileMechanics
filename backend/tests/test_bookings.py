"""Backend tests for M&A Precision Mechanical API."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ma-precision-preview.preview.emergentagent.com').rstrip('/')


@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ===== Health =====
class TestHealth:
    def test_health(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"
        assert "time" in data

    def test_root(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "message" in data
        assert "M&A" in data["message"] or "Precision" in data["message"]


# ===== Bookings =====
VALID_PAYLOAD = {
    "full_name": "TEST_John Smith",
    "phone": "437-555-1212",
    "email": "TEST_john@example.com",
    "service_type": "Inspection",
    "vehicle": "2019 Honda Civic",
    "preferred_datetime": "2026-02-01 10:00 AM",
    "issue": "Engine making strange noise on cold start",
}


class TestBookings:
    created_id = None

    def test_create_booking_valid(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/bookings", json=VALID_PAYLOAD, timeout=30)
        assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
        data = r.json()
        # Check required fields
        assert "id" in data
        assert len(data["id"]) > 10  # uuid
        assert data["full_name"] == VALID_PAYLOAD["full_name"]
        assert data["service_type"] == "Inspection"
        assert "email_sent" in data
        assert isinstance(data["email_sent"], bool)
        # Crucial: _id MUST not leak
        assert "_id" not in data, f"Mongo _id leaked in response: {data}"
        TestBookings.created_id = data["id"]

    def test_create_booking_invalid_service_type(self, api_client):
        payload = {**VALID_PAYLOAD, "service_type": "Foo"}
        r = api_client.post(f"{BASE_URL}/api/bookings", json=payload, timeout=15)
        assert r.status_code == 400, f"Expected 400 got {r.status_code}: {r.text}"

    def test_create_booking_invalid_email(self, api_client):
        payload = {**VALID_PAYLOAD, "email": "not-an-email"}
        r = api_client.post(f"{BASE_URL}/api/bookings", json=payload, timeout=15)
        assert r.status_code == 422, f"Expected 422 got {r.status_code}: {r.text}"

    def test_create_booking_missing_fields(self, api_client):
        payload = {"full_name": "Only Name"}
        r = api_client.post(f"{BASE_URL}/api/bookings", json=payload, timeout=15)
        assert r.status_code == 422

    def test_list_bookings_no_objectid(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/bookings", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Should have at least one booking from prior test"
        # No _id leak
        for b in data:
            assert "_id" not in b, f"Mongo _id leaked: {b}"
            assert "id" in b
            assert "created_at" in b

    def test_list_bookings_sorted_desc(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/bookings", timeout=20)
        data = r.json()
        if len(data) >= 2:
            # created_at must be descending
            times = [b["created_at"] for b in data]
            assert times == sorted(times, reverse=True), "Bookings not sorted desc by created_at"

    def test_created_booking_retrievable(self, api_client):
        assert TestBookings.created_id, "Need created_id from earlier test"
        r = api_client.get(f"{BASE_URL}/api/bookings", timeout=20)
        data = r.json()
        ids = [b["id"] for b in data]
        assert TestBookings.created_id in ids, "Created booking not found in list"

    def test_all_service_types_accepted(self, api_client):
        for svc in ["Diagnostics", "Repair", "Maintenance"]:
            payload = {**VALID_PAYLOAD, "service_type": svc, "full_name": f"TEST_{svc}_user"}
            r = api_client.post(f"{BASE_URL}/api/bookings", json=payload, timeout=30)
            assert r.status_code == 200, f"{svc} failed: {r.status_code} {r.text}"
            assert r.json()["service_type"] == svc
