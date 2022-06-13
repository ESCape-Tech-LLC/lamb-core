from __future__ import annotations

import logging
from typing import Union, NewType, Optional

from django.conf import settings
from django.http import HttpRequest

# Lamb Framework
from lamb.utils import LambRequest

import geoip2
import lazy_object_proxy
from geoip2 import models
from ipware import get_client_ip
from geoip2.errors import AddressNotFoundError
from geoip2.database import Reader

logger = logging.getLogger(__name__)


__all__ = ["get_country_info", "get_city_info", "get_asn_info"]


# utils
ProxyReader = NewType("ProxyReader", Reader)


def _geoip2_reader(db_path: Optional[str]) -> Optional[Reader]:
    try:
        logger.info(f"max_mind. loading database on path: {db_path}")
        return geoip2.database.Reader(db_path)
    except Exception as e:
        logger.warning(f"max_mind. database loading failed: {e}")
        return None


def _resolve_ip_source(value: Union[str, LambRequest]) -> Optional[str]:
    try:
        if isinstance(value, str):
            ip_address = value
        elif isinstance(value, HttpRequest):
            ip_address, _ = get_client_ip(value)
        else:
            logger.warning(f"max_mind. resolve_ip_source - invalid object received: {value} of type {value.__class__}")
            ip_address = None
        return ip_address

    except Exception as e:
        logger.warning(f"max_mind. resolve_ip_source - failed to resolve source with error: {e}")
        return None


def _get_info(source: Union[str, LambRequest], reader: ProxyReader, reader_name: str):
    if reader is None or reader == None:  # noqa
        logger.debug(f"max_mind. {reader_name}: break -> reader is None")
        return None

    # check ip address
    ip_address = _resolve_ip_source(source)
    if ip_address is None:
        logger.debug(f"max_mind. {reader_name}: break - > ip_address is None")
        return None

    # try resolve
    try:
        _method_map = {
            _geoip2_db_reader_city: "city",
            _geoip2_db_reader_country: "country",
            _geoip2_db_reader_asn: "asn",
        }
        result = getattr(reader, _method_map[reader])(ip_address=ip_address)
        return result
    except AddressNotFoundError:
        logger.debug(f"max_mind. {reader_name}: break -> the ip_address = {ip_address} is not found in database")
        return None
    except Exception as e:
        logger.warning(f"max_mind. {reader_name}: break -> exception: {e} of type {e.__class__}")
        return None


# globals
# - initialized once for performance
# - lambda used for lazy settings load
_geoip2_db_reader_city: ProxyReader = lazy_object_proxy.Proxy(
    lambda: _geoip2_reader(db_path=settings.LAMB_GEOIP2_DB_CITY)
)

_geoip2_db_reader_country: ProxyReader = lazy_object_proxy.Proxy(
    lambda: _geoip2_reader(db_path=settings.LAMB_GEOIP2_DB_COUNTRY)
)

_geoip2_db_reader_asn: ProxyReader = lazy_object_proxy.Proxy(
    lambda: _geoip2_reader(db_path=settings.LAMB_GEOIP2_DB_ASN)
)


# public interface
def get_city_info(source: Union[str, LambRequest]) -> Optional[models.City]:
    return _get_info(source=source, reader=_geoip2_db_reader_city, reader_name="geoip2_db_city")


def get_country_info(source: Union[str, LambRequest]) -> Optional[models.Country]:
    return _get_info(source=source, reader=_geoip2_db_reader_country, reader_name="geoip2_db_country")


def get_asn_info(source: Union[str, LambRequest]) -> Optional[models.ASN]:
    return _get_info(source=source, reader=_geoip2_db_reader_asn, reader_name="geoip2_db_asn")
