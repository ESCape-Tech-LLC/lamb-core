# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import requests
import copy

from typing import Optional, Any, Callable, List, Tuple
from dataclasses import dataclass

from datetime import datetime
from furl import furl
from lazy import lazy
from sqlalchemy.orm.session import Session as SASession
from lamb.exc import ServerError, ImproperlyConfiguredError, ExternalServiceError, ApiError
from lamb.utils import dpath_value, compact, masked_dict
from lamb.acquiring.base import AbstractPaymentEngine


__all__ = [
    'RBSCallError', 'RBSResponse'
]

logger = logging.getLogger(__name__)

# @dataclass(frozen=True)
# class RBSErrorInfo(object):
#     error_code: int
#     error_message: Optional[str] = None
#
#


@dataclass(frozen=True)
class RBSResponse(object):
    content: dict

    def __post_init__(self):
        # validate format
        try:
            _ = self.error_code
            _ = self.error_message
        except ApiError as e:
            raise ExternalServiceError('RBS call failede due invalid response format') from e

    @property
    def error_code(self) -> int:
        return dpath_value(self.content, 'errorCode', req_type=int, default=0)

    @property
    def error_message(self) -> Optional[str]:
        return dpath_value(self.content, 'errorMessage', req_type=str, default=None)


class RBSCallError(ExternalServiceError):
    rbs_response: RBSResponse

    def __init__(self, *args, rbs_response: RBSResponse, **kwargs):
        super().__init__(*args, **kwargs)
        self.rbs_response = rbs_response


def _default_currency_multiplier_callback(currency_iso4217: int) -> int:
    mapper = {
        643: 100  # RUR
    }
    if currency_iso4217 not in mapper:
        logger.error(f'Unknown default currency multiplier callback code={currency_iso4217}')
        raise ImproperlyConfiguredError
    return mapper[currency_iso4217]


@dataclass(frozen=True)
class RBSPaymentEngine(object):

    endpoint: str
    merchant_token: Optional[str] = None
    merchant_login: Optional[str] = None
    merchant_password: Optional[str] = None
    callback_hmac_key: Optional[str] = None
    currency_multiplier_callback: Callable[[int], int] = _default_currency_multiplier_callback

    # utilities
    def __post_init__(self):
        # check connection
        if self.merchant_token is not None:
            if len(self.merchant_token) == 0:
                logger.error('merchant_token is empty')
                raise ImproperlyConfiguredError
        else:
            if any([
                not isinstance(self.merchant_login, str),
                not isinstance(self.merchant_password, str),
                len(self.merchant_login) == 0,
                len(self.merchant_password) == 0
            ]):
                logger.error(f'invalid marchant params: merchant_login={self.merchant_login}, password={self.merchant_password}')
                raise ImproperlyConfiguredError

    def _make_request(self, method: str, params: dict = None):
        logger.debug(f'Execute RBS request, method={method} params={params}')

        try:
            # prepare params
            if params is None:
                params = {}

            if self.merchant_token is not None:
                params['token'] = self.merchant_token
            else:
                params['userName'] = self.merchant_login
                params['password'] = self.merchant_password
            params = compact(params)
            _masked_params = masked_dict(params, 'password', 'token')
            logger.info(f'RBS call params: {_masked_params}')

            # execute request
            method_url = furl(self.endpoint)
            method_url.path.add(method)
            method_url = method_url.url
            response = requests.get(url=method_url, params=params)

            if response.status_code != 200:
                logger.error(f'RBS call to method {method} failed due invalid http status code={response.status_code}, '
                             f'content={response.content}')
                raise ExternalServiceError('RBS service call failed')
            response = response.json()
            logger.debug(f'RBS JSON response raw: [{method}] -> {response}')

            # check for proper data type
            if not isinstance(response, dict):
                logger.error(f'RBS call to method {method} failed due invalid response format, data={response}')
                raise ExternalServiceError('RBS service call failed')

            # small hack cause RBS is so wonderful about error processing guys!!!!
            if 'ErrorCode' in response:
                response['errorCode'] = response.pop('ErrorCode')
            if 'ErrorMessage' in response:
                response['errorMessage'] = response.pop('ErrorMessage')
            logger.debug(f'RBS JSON response normalized: {response}')

            response = RBSResponse(content=response)
            logger.info(f'RBS JSON response: [{method}] -> {response}')

            return response
        except ApiError as e:
            raise e from e
        except requests.RequestException as e:
            logger.error('RBS %s service failed with network exception: %s' % (method, e))
            raise ExternalServiceError('RBS service %s failed with network exception' % method) from e
        except Exception as e:
            logger.error('RBS %s service failed due unknown reason: <%s> %s' % (method, e.__class__.__name__, e))
            raise ExternalServiceError('RBS service %s failed with unknown error' % method)

    # methods
    def register(self,
                 amount: float,
                 success_uri: str,
                 order_number: Any,
                 currency: int = 643,
                 fail_uri: Optional[str] = None,
                 description: Optional[str] = None,
                 language: Optional[str] = None,
                 page_view: Optional[str] = None,
                 client_id: Optional[str] = None,
                 child_merchant_login: Optional[str] = None,
                 json_params: Optional[dict] = None,
                 session_timeout_secs: Optional[int] = None,
                 expiration_date: Optional[datetime] = None,
                 binding_id: Optional[str] = None,
                 features: Optional[str] = None
                 ) -> Tuple[RBSResponse, str, str]:
        """ Register payment and returns (rbs_response, orderId, formUrl) """
        # make request
        result = self._make_request(
            method='register.do',
            params={
                'orderNumber': str(order_number) if order_number is not None else None,
                'amount': int(amount * self.currency_multiplier_callback(currency)),
                'currency': currency,
                'returnUrl': success_uri,
                'failUrl': fail_uri,
                'description': description,
                'language': language,
                'pageView': page_view,
                'clientId': str(client_id) if client_id is not None else None,
                'merchantLogin': child_merchant_login,
                'jsonParams': json_params,
                'sessionTimeoutSecs': session_timeout_secs,
                'expirationDate': expiration_date.strftime('%Y-%m-%dT%H:%M:%S') if isinstance(expiration_date, datetime) else None,
                'bindingId': str(binding_id) if binding_id is not None else None,
                'features': features
            }
        )

        # validate status
        if result.error_code != 0:
            raise RBSCallError('RBS failed due invalid error_code', rbs_response=result)

        # validate response format
        try:
            order_id = dpath_value(result.content, 'orderId', str)
            form_url = dpath_value(result.content, 'formUrl', str)
            return result, order_id, form_url
        except ApiError as e:
            logger.error(f'RBS content: {result.content}')
            raise RBSCallError('RBS failed due invalid response format', rbs_response=result) from e

    def get_status(self, rbs_order_id: str, order_number: Optional[Any] = None, language: Optional[str] = None) -> RBSResponse:
        """ Obtain extended payment status from RBS """
        # make request
        result = self._make_request(
            method='getOrderStatusExtended.do',
            params={
                'orderId': rbs_order_id,
                'orderNumber': str(order_number) if order_number is not None else None,
                'language': language,
            }
        )

        # validate status
        if result.error_code != 0:
            raise RBSCallError('RBS failed due invalid error_code', rbs_response=result)

        # import json
        return result
