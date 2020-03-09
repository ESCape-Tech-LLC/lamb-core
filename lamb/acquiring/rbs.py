# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import requests
import copy
import hmac
import hashlib
import re

from typing import Optional, Any, Callable, List, Tuple, Dict
from dataclasses import dataclass

from datetime import datetime
from furl import furl
from lazy import lazy
from sqlalchemy.orm.session import Session as SASession
from lamb.exc import ServerError, ImproperlyConfiguredError, ExternalServiceError, ApiError
from lamb.utils import dpath_value, compact, masked_dict
from lamb.acquiring.base import AbstractPaymentEngine


__all__ = [
    'RBSCallError', 'RBSResponse', 'determine_card_type'
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


_DEFAULT_MAPPING = {
    'VISA': re.compile(r'^4[0-9]{12}(?:[0-9]{3})?$'),
    'MASTER CARD': re.compile(r'^(?:5[1-5][0-9]{2}|222[1-9]|22[3-9][0-9]|2[3-6][0-9]{2}|27[01][0-9]|2720)[0-9]{12}$'),
    'AMERICAN EXPRESS': re.compile(r'^3[47][0-9]{13}$'),
    'JCB': re.compile(r'^(?:2131|1800|35\d{3})\d{11}$'),
    'DINERS CLUB': re.compile(r'^3(?:0[0-5]|[68][0-9])[0-9]{11}$'),
    'DISCOVER': re.compile(r'^6(?:011|5[0-9]{2})[0-9]{12}$ '),
    'MIR': re.compile(r'^220[0-4][0-9]{12}$')
    }


def determine_card_type(pan: str, mapping: Dict[str, Any] = _DEFAULT_MAPPING) -> Optional[str]:
    for result, regex in mapping.items():
        m = regex.match(pan)
        if regex.match(pan) is not None:
            return result
    return None


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

    def validate_callback(self, params: Dict[str, Any]) -> Tuple[str, str]:
        # construct check sum control string
        checksum_control_params = {k: v for k, v in params.items() if k != 'checksum'}
        checksum_control_params_sorted_keys = sorted(list(checksum_control_params.keys()), key=str.lower)
        checksum_control_items = ['%s;%s' % (k, checksum_control_params[k]) for k in
                                  checksum_control_params_sorted_keys]
        checksum_control_string = ';'.join(checksum_control_items) + ';'

        calculated_checksum = hmac.new(
            self.callback_hmac_key.encode('utf-8'),
            msg=checksum_control_string.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest().upper()

        # compare against received checksum
        received_checksum = dpath_value(params, 'checksum', str).upper()
        if received_checksum != calculated_checksum:
            get_params = '&'.join(['%s=%s' % (k, v) for k, v in params.items()])
            raise InvalidParamValueError(
                'RBS callback failed due check sums not equal <params=%s, received=%s, calculated=%s>' % (
                    get_params, received_checksum, calculated_checksum))

        # check operation type and status
        operation = dpath_value(params, 'operation', req_type=str)
        # if operation not in ['approved', 'deposited', 'reversed', 'refunded']:
        #     raise InvalidParamValueError('RBS callback failed due unknown operation type %s' % operation)
        status = dpath_value(params, 'status', req_type=int)
        if status not in [0, 1]:
            raise InvalidParamValueError('RBS callback failed due unknown status %s' % status)

        # extract params
        logger.debug(f'did validate checksum for payment callback: {params} -> {calculated_checksum, operation, status}')
        return dpath_value(params, 'mdOrder', str), dpath_value(params, 'orderNumber', str)

    def get_bindings(self, client_id: str) -> List[Dict[str, Any]]:
        result = self._make_request(
            method='getBindings.do',
            params={
                'clientId': client_id
            }
        )

        # validate status
        if result.error_code not in [0, 2]:
            raise RBSCallError('RBS failed due invalid error_code', rbs_response=result)
        try:
            bindings = dpath_value(result.content, 'bindings', list)
            return bindings
        except ApiError as e:
            logger.error(f'RBS content: {result.content}')
            raise RBSCallError('RBS failed due invalid response format', rbs_response=result) from e
