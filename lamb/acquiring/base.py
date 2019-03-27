# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
from sqlalchemy.orm.session import Session as SASession

from lamb.exc import ServerError

__all__ = [
]

logger = logging.getLogger(__name__)


__all__ = ['AbstractPaymentEngine']


class AbstractPaymentEngine(object):

    db_session: SASession

    def __init__(self, db_session: SASession, **kwargs):
        self.db_session = db_session
        if not isinstance(self.db_session, Session):
            logger.warning('Improperly configured AbstractPaymentEngine - invalid db_session param type')
            raise ServerError('Improperly configured server side call')

    # no-hold payments
    # def register_payment(self, payment, session_timeout):
    #     """ Register payment on acquiring side
    #
    #     Method responsible for register payment on side of acquiring backend
    #
    #     :param payment: Payment item to be registered
    #     :type payment: api.model.Payment
    #     :param session_timeout: Timeout for payment form
    #     :type session_timeout: int
    #     :return: Prepared payment form URL
    #     :rtype: str
    #     """
    #     raise NotRealizedMethodError('Abstract method should be implemented in concrete subclass engine')
    #
    #
    # def update_payment_status(self, payment):
    #     """ Update payment status
    #
    #     Method responsible for update payment status on side of engine and sync it database
    #
    #     :param payment: Payment item to be updated
    #     :type payment: api.model.Payment
    #     :rtype: None
    #     """
    #     raise NotRealizedMethodError('Abstract method should be implemented in concrete subclass engine')
    #
    #
    # def refund_payment(self, payment):
    #     """ Refund payment
    #
    #     Method responsible for refund payment
    #
    #     :param payment: Payment item to refund
    #     :type payment: api.model.Payment
    #     :rtype: None
    #     """
    #     raise NotRealizedMethodError('Abstract method should be implemented in concrete subclass engine')
    #
    #
    # def get_bindings(self, client, product):
    #     """ Request bind to client cards list
    #
    #     :param client: Client to request bindings
    #     :type client: api.model.Client
    #     :param product: Product to request bindings within
    #     :type product: api.model.Product
    #     :return: Raw service response
    #     :rtype: dict
    #     """
    #     raise NotRealizedMethodError('Abstract method should be implemented in concrete subclass engine')
    #
    #
    # def process_callback(self, **kwargs):
    #     """ Process callback call from engine
    #
    #     Method responsible for processing callback service request from engine.
    #
    #     :param kwargs: Payment item to be registered
    #     :type kwargs: dict
    #     :return: Prepared payment form URL
    #     :rtype: str
    #     """
    #     raise NotRealizedMethodError('Abstract method should be implemented in concrete subclass engine')