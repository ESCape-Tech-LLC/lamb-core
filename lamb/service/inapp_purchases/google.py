from __future__ import annotations

import json
from typing import Union
from datetime import datetime

# Lamb Framework
from lamb.exc import (
    ExternalServiceError,
    InvalidParamValueError,
    InvalidBodyStructureError,
)

from google.oauth2 import service_account as google_service_account
from google.auth.transport.requests import AuthorizedSession

from .base import PurchaseData, InAppAbstract, SubscriptionStatus


class InAppGoogle(InAppAbstract):

    scopes = ("https://www.googleapis.com/auth/androidpublisher",)
    uri_base = "https://www.googleapis.com/androidpublisher/v3/applications"
    uri_product = "/%packageName%/purchases/products/%productId%/tokens/%token%"
    uri_subscription = "/%packageName%/purchases/subscriptions/%subscriptionId%/tokens/%token%"

    package_name: str
    product_id: str
    purchase_token: str
    service_account_info: dict = None
    service_account_file: str = None
    is_subscription: bool

    _credentials: google_service_account.Credentials = None
    _session: AuthorizedSession = None
    _raw_data: dict = None

    def __init__(self, receipt_data: dict, service_account: Union[str, dict], is_subscription: bool = True):
        """
        :param receipt_data: dict containing `packageName`, `productId`, and `purchaseToken` values
        :param service_account: Path to json file or dict containing service account data, i.e. private key
        :param is_subscription: Flag that determines if a purchase is subscription
        """
        try:
            self.package_name = receipt_data["packageName"]
            self.product_id = receipt_data["productId"]
            self.purchase_token = receipt_data["purchaseToken"]
        except KeyError:
            raise InvalidBodyStructureError(
                "Invalid receipt_data structure. Not all packageName, productId, " "purchaseToken are present"
            )

        if isinstance(service_account, str):
            self.service_account_file = service_account
        elif isinstance(service_account, dict):
            self.service_account_info = service_account
        else:
            raise InvalidParamValueError("Invalid service_account type")

        self.is_subscription = is_subscription

    def _generate_credentials(self) -> google_service_account.Credentials:
        if self.service_account_file is not None:
            self._credentials = google_service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.scopes
            )
        else:
            self._credentials = google_service_account.Credentials.from_service_account_info(
                self.service_account_info, scopes=self.scopes
            )
        return self._credentials

    def _get_session(self) -> AuthorizedSession:
        if self._session is None:
            if self._credentials is None:
                self._generate_credentials()
            self._session = AuthorizedSession(self._credentials)
        return self._session

    def _create_request_uri(self):
        if self.is_subscription:
            uri_part = self.uri_subscription
        else:
            uri_part = self.uri_product

        request_uri = self.uri_base + uri_part.replace("%packageName%", self.package_name).replace(
            "%productId%", self.product_id
        ).replace("%subscriptionId%", self.product_id).replace("%token%", self.purchase_token)

        return request_uri

    def _make_request(self) -> dict:

        request_uri = self._create_request_uri()

        response = self._get_session().get(request_uri)

        try:
            data = json.loads(response.content)
        except json.decoder.JSONDecodeError:
            raise ExternalServiceError("Unable to decode response for inapp purchase from Google server")

        if not response.ok:
            try:
                error_reason = data["error"]["errors"][0]["reason"]
                if error_reason == "purchaseTokenDoesNotMatchPackageName":
                    raise ExternalServiceError(
                        "Error while processing data. Purchase token does not " "match package name"
                    )
                elif error_reason == "invalid":
                    raise ExternalServiceError("Error while processing data. Invalid token value")
                else:
                    raise ValueError
            except (KeyError, IndexError, ValueError):
                raise ExternalServiceError("Error while processing data. Unable to identify the reason")

        return data

    def _make_request_acknowledge(self, fail_silent: bool):

        request_uri = self._create_request_uri()
        request_uri += ":acknowledge"

        response = self._get_session().post(request_uri)

        if not response.ok and not fail_silent:
            raise ExternalServiceError("Error while trying to acknowledge purchase")

    def _get_data_raw(self):
        if self._raw_data is None:
            self._raw_data = self._make_request()
        return self._raw_data

    def refresh(self):
        self._raw_data = self._make_request()

    def get_purchase_data(self) -> PurchaseData:
        def _get_status(data, expiry_date):
            purchase_state = self._parse_data(data, "purchaseState")

            if self._parse_data(data, "cancelReason") is not None or purchase_state == 1:
                return SubscriptionStatus.CANCELLED

            if self._parse_data(data, "paymentState") == 0 or purchase_state == 2:
                return SubscriptionStatus.PAYMENT_PENDING

            if expiry_date is None:
                expiry_date = self._get_expiry_date(data, "expiryTimeMillis")

            if expiry_date is not None:
                if expiry_date > datetime.now():
                    return SubscriptionStatus.ACTIVE
                else:
                    return SubscriptionStatus.EXPIRED
            else:
                return SubscriptionStatus.UNKNOWN

        receipt = self._get_data_raw()
        active_until = self._get_expiry_date(receipt, "expiryTimeMillis")

        purchase_data = PurchaseData(
            package_name=self.package_name,
            product_id=self.product_id,
            status=_get_status(receipt, active_until),
            active_until=active_until,
            order_id=self.purchase_token,
        )

        return purchase_data

    def get_purchase_data_raw(self) -> dict:
        return self._get_data_raw()

    def acknowledge(self, fail_silent: bool = True):
        self._make_request_acknowledge(fail_silent=fail_silent)
