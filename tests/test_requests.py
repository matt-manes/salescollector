import requests
from pathier import Pathier

root = Pathier(__file__).parent
root.parent.add_to_PATH()
from etsy_requests import EtsyRequests


def test_ping():
    response: requests.Response = EtsyRequests.ping()
    assert response.status_code == 200
    assert response.json()["application_id"]
