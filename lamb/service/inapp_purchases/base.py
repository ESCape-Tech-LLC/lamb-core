# -*- coding: utf-8 -*-

from datetime import datetime
from enum import Enum
from typing import Optional

from dataclasses import dataclass


class SubscriptionStatus(Enum):
    PAYMENT_PENDING = 'PAYMENT_PENDING'
    ACTIVE = 'ACTIVE'
    CANCELLED = 'CANCELLED'
    EXPIRED = 'EXPIRED'
    UNKNOWN = 'UNKNOWN'


@dataclass
class PurchaseData:
    package_name: str
    product_id: str
    status: SubscriptionStatus
    active_until: Optional[datetime]
    order_id: str


class InAppAbstract:

    @staticmethod
    def _parse_data(data, key, sort_by=None):
        try:
            if not sort_by:
                return data[key]
            else:
                return sorted(data[key], key=lambda x: x[sort_by], reverse=True)[0]
        except (KeyError, TypeError):
            return None

    @staticmethod
    def _get_expiry_date(data, key):
        try:
            return datetime.fromtimestamp(int(InAppAbstract._parse_data(data, key)) / 1000.)
        except TypeError:
            return None

    def refresh(self):
        raise NotImplementedError

    def get_purchase_data(self) -> PurchaseData:
        raise NotImplementedError

    def get_purchase_data_raw(self) -> dict:
        raise NotImplementedError

