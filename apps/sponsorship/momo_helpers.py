import uuid, random, requests

BASE_URL = "https://sandbox.momodeveloper.mtn.com"  # Change to (https://momodeveloper.mtn.com) URL for live


def generate_uuid():
    return str(uuid.uuid4())


def momo_headers(subscription_key, token=None, ref_id=None):
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-Target-Environment"] = "sandbox"  # Change to 'production' for live
    if ref_id:
        headers["X-Reference-Id"] = ref_id
    return headers


def create_access_token(reference_id, api_key, subscription_key):
    """Generate access token using stored API user credentials."""
    url = f"{BASE_URL}/collection/token/"
    auth = requests.auth.HTTPBasicAuth(reference_id, api_key)
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}
    res = requests.post(url, headers=headers, auth=auth, timeout=10)
    if res.status_code == 200:
        return res.json().get("access_token")
    return None


def request_to_pay(access_token, subscription_key, phone, amount, transaction_id):
    """Initiate payment to MTN MoMo API."""
    url = f"{BASE_URL}/collection/v1_0/requesttopay"
    headers = momo_headers(subscription_key, access_token, transaction_id)
    external_id = str(random.randint(10000000, 99999999))
    body = {
        "amount": str(amount),
        "currency": "EUR",
        "externalId": external_id,
        "payer": {"partyIdType": "MSISDN", "partyId": phone},
        "payerMessage": "Umeskia Softwares MTN Payment",
        "payeeNote": "Thank you for using our system",
    }
    res = requests.post(url, json=body, headers=headers, timeout=10)
    return res.status_code, res.text
