import random
import uuid
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://momoapi.mtn.com"


def _headers(token=None, ref_id=None):
    headers = {
        "Ocp-Apim-Subscription-Key": settings.SUBSCRIPTION_KEY.strip(),  # .strip() saves lives
        "X-Target-Environment": "mtnuganda",   # THIS LINE IS ABSOLUTELY REQUIRED
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if ref_id:
        headers["X-Reference-Id"] = ref_id
    return headers


def create_access_token():
    url = f"{BASE_URL}/collection/token/"
    auth = (settings.MOMO_API_USER.strip(), settings.MOMO_API_KEY.strip())

    try:
        response = requests.post(
            url,
            headers=_headers(),           # Includes X-Target-Environment
            auth=auth,
            timeout=30
        )

        # DEBUG LOG — keep this for now
        logger.info(f"TOKEN REQUEST → {response.status_code} | {response.text[:300]}")

        if response.status_code in (200, 201):
            token = response.json().get("access_token")
            if token:
                logger.info("TOKEN SUCCESS")
                return token

        logger.error(f"TOKEN FAILED → {response.status_code} {response.text}")
        return None

    except Exception as e:
        logger.exception(f"TOKEN EXCEPTION → {e}")
        return None


def request_to_pay(phone: str, amount: int, reference_id: str):
    token = create_access_token()
    if not token:
        return 500, "Token creation failed", None

    url = f"{BASE_URL}/collection/v1_0/requesttopay"
    external_id = str(random.randint(10000000, 99999999))

    payload = {
        "amount": str(amount),
        "currency": "UGX",
        "externalId": external_id,
        "payer": {"partyIdType": "MSISDN", "partyId": phone},
        "payerMessage": "Pendeza Sponsorship",
        "payeeNote": "Thank you!",
    }

    try:
        r = requests.post(url, json=payload, headers=_headers(token, reference_id), timeout=30)
        logger.info(f"RTP → {r.status_code} | Ref: {reference_id}")
        return r.status_code, r.text, external_id
    except Exception as e:
        logger.exception("RTP exception")
        return 500, str(e), None

def get_transaction_status(reference_id: str):
    """Used by polling endpoint"""
    token = create_access_token()
    if not token:
        return "PENDING"

    url = f"{BASE_URL}/collection/v1_0/requesttopay/{reference_id}"
    try:
        r = requests.get(url, headers=_headers(token), timeout=10)
        if r.status_code == 200:
            return r.json().get("status", "PENDING")
    except Exception:
        pass
    return "PENDING"