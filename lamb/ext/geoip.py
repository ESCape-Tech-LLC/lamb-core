# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import geoip2

from typing import Optional
from geoip2.database import Reader
from django.conf import settings

from lamb import exc

logger = logging.getLogger(__name__)


# GeoIP2
_geoip2_city_reader = None


# def _city_reader() -> Reader:
#     global _geoip2_city_reader
#     if _geoip2_city_reader is None:
        # _geoip2_city_reader = geoip2.database.Reader(settings.)
def _get_geoip2_reader_database_city() -> geoip2.database.Reader:
    global _geoip2_city_reader
    if _geoip2_city_reader is None:
        _geoip2_city_reader = geoip2.database.Reader(settings.DTS_GEOIP2_DB_CITY)
    return _geoip2_city_reader


def geoip2_info_city(ip: str) -> Optional[geoip2.models.City]:
    try:
        return _get_geoip2_reader_database_city().city(ip)
    except geoip2.errors.GeoIP2Error as e:
        logger.warning(f'could not determine city: {e}')
        return None


_geoip2_country_reader = None


def _get_geoip2_reader_database_country() -> geoip2.database.Reader:
    global _geoip2_country_reader
    if _geoip2_country_reader is None:
        _geoip2_country_reader = geoip2.database.Reader(settings.DTS_GEOIP2_DB_COUNTRY)
    return _geoip2_country_reader


def geoip2_info_country(ip: str) -> Optional[geoip2.models.Country]:
    try:
        return _get_geoip2_reader_database_country().country(ip)
    except geoip2.errors.GeoIP2Error as e:
        logger.warning(f'could not determine country: {e}')
        return None


def get_geoname_id_for_ip(ip_address: str) -> Optional[int]:
    country_info = geoip2_info_country(ip_address)
    logger.debug(f'country: {country_info}')
    try:
        country_geoname_id = country_info.country.geoname_id
    except:
        country_geoname_id = None

    return country_geoname_id


def _get_ip_from_request(request: DTSRequest) -> str:
    ip_address, is_routable = get_client_ip(request)
    if settings.DEBUG and settings.DTS_OVERRIDE_GEONAME_LOCAL_IP is not None:
        result = settings.DTS_OVERRIDE_GEONAME_LOCAL_IP
        logger.warning(f'ip address replaced for debug env: {ip_address} -> {result}')
    else:
        result = ip_address

    return result


def geoip2_country_geoname_id_for_request(request: DTSRequest) -> Optional[int]:
    ip_address = _get_ip_from_request(request)
    # ip_address, is_routable = get_client_ip(request)
    # # logger.info(f'catalog requested from: {ip_address, is_routable}')
    # if settings.DEBUG and sys.platform.startswith('darwin'):
    #     ip_address = '95.165.172.199'
    #     logger.warning(f'ip address replaced for local debug: {ip_address}')

    return get_geoname_id_for_ip(ip_address)


def get_country_info_for_request(request: DTSRequest):
    fake_ip = dpath_value(request.GET, 'fake_ip', str, default=None)
    if not fake_ip:
        ip_address = _get_ip_from_request(request)
    else:
        ip_address = fake_ip
    return geoip2_info_country(ip_address)