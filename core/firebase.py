import base64
import binascii
import json
import os
from threading import Lock

import firebase_admin
from django.core.exceptions import ImproperlyConfigured
from firebase_admin import credentials

_initialization_lock = Lock()


def _credential_from_environment():
    encoded = os.environ.get("FIREBASE_SERVICE_ACCOUNT_B64", "").strip()
    if not encoded:
        return None
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        service_account = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise ImproperlyConfigured("FIREBASE_SERVICE_ACCOUNT_B64 is not valid base64-encoded JSON.") from exc

    required = {"type", "project_id", "private_key", "client_email", "token_uri"}
    if service_account.get("type") != "service_account" or not required.issubset(service_account):
        raise ImproperlyConfigured("Firebase service-account credentials are incomplete or invalid.")

    expected_project = os.environ.get("FIREBASE_PROJECT_ID", "pendezaconnect")
    if service_account["project_id"] != expected_project:
        raise ImproperlyConfigured("Firebase credentials do not match FIREBASE_PROJECT_ID.")
    return credentials.Certificate(service_account)


def get_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    with _initialization_lock:
        try:
            return firebase_admin.get_app()
        except ValueError:
            project_id = os.environ.get("FIREBASE_PROJECT_ID", "pendezaconnect")
            return firebase_admin.initialize_app(
                _credential_from_environment(),
                {"projectId": project_id, "httpTimeout": 15},
            )
