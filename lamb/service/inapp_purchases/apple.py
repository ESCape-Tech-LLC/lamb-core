# -*- coding: utf-8 -*-
import json
from datetime import datetime

import requests
from lamb.exc import ExternalServiceError

from .base import InAppAbstract, PurchaseData, SubscriptionStatus
from .exc import InAppAppleSandboxError


class InAppApple(InAppAbstract):

    uri_sandbox = 'https://sandbox.itunes.apple.com/verifyReceipt'
    uri_production = 'https://buy.itunes.apple.com/verifyReceipt'

    receipt: str
    shared_secret: str
    exclude_old_transactions: bool
    no_sandbox: bool

    _raw_data: dict = None

    def __init__(self, receipt: str, shared_secret: str, exclude_old_transactions: bool = False,
                 no_sandbox: bool = False):
        """
        :param receipt: base64 encoded receipt
        :param shared_secret: Application's shared secret
        :param exclude_old_transactions: Set this value to true for the raw data to include only the latest renewal
            transaction for any subscriptions. Does not affect get_purchase_data return
        :param no_sandbox: Determines whether sandbox request should be skipped
        """

        self.receipt = receipt
        self.shared_secret = shared_secret
        self.exclude_old_transactions = exclude_old_transactions
        self.no_sandbox = no_sandbox

    def _make_request(self, sandbox: bool = False) -> dict:
        request_uri = InAppApple.uri_sandbox if sandbox else InAppApple.uri_production
        query = {
            'receipt-data': self.receipt,
            'password': self.shared_secret,
            'exclude-old-transactions': self.exclude_old_transactions
        }
        response = requests.post(request_uri, data=json.dumps(query))

        if not response.ok:
            raise ExternalServiceError('Unable to get a response for inapp purchase from Apple server')

        try:
            data = json.loads(response.content)
        except json.decoder.JSONDecodeError:
            raise ExternalServiceError('Unable to decode a response for inapp purchase from Apple server')

        if 'status' not in data:
            raise ExternalServiceError('Malformed response for inapp purchase from Apple server')
        elif data['status'] == 21007:
            if self.no_sandbox:
                raise InAppAppleSandboxError
            else:
                data = self._make_request(sandbox=True)
        elif data['status'] == 21002:
            raise ExternalServiceError('The data in the receipt was malformed or the Apple service experienced a '
                                       'temporary issue')
        elif data['status'] != 0:
            raise ExternalServiceError('Unknown error for inapp purchase from Apple server')

        return data

    def _get_data_raw(self):
        if self._raw_data is None:
            self._raw_data = self._make_request()
        return self._raw_data

    def refresh(self):
        self._raw_data = self._make_request()

    def get_purchase_data(self) -> PurchaseData:

        def _get_status(in_app_data, expires_date):
            if self._parse_data(in_app_data, 'cancellation_date_ms') is not None:
                return SubscriptionStatus.CANCELLED

            if expires_date is None:
                expires_date = self._get_expiry_date(in_app_data, 'expires_date_ms')

            if expires_date is not None:
                if expires_date > datetime.now():
                    return SubscriptionStatus.ACTIVE
                else:
                    return SubscriptionStatus.EXPIRED
            else:
                return SubscriptionStatus.UNKNOWN

        receipt = self._parse_data(self._get_data_raw(), 'receipt')
        try:
            latest_receipt = self._parse_data(self._get_data_raw(), 'latest_receipt_info')[0]
        except (IndexError, TypeError):
            latest_receipt = self._parse_data(receipt, 'in_app', sort_by='expires_date_ms')
        active_until = self._get_expiry_date(latest_receipt, 'expires_date_ms')

        purchase_data = PurchaseData(
            package_name=self._parse_data(receipt, 'bundle_id'),
            product_id=self._parse_data(latest_receipt, 'product_id'),
            status=_get_status(latest_receipt, active_until),
            active_until=active_until,
            order_id=str(self._parse_data(latest_receipt, 'original_transaction_id'))
        )

        return purchase_data

    def get_purchase_data_raw(self) -> dict:
        return self._get_data_raw()
