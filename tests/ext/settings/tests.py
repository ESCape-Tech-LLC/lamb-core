from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings

from lamb.ext.settings import AbstractSettingsStorage, AbstractSettingsValue
from tests.testcases import LambTestCase


class SettingsValue(AbstractSettingsValue):
    __table_class__ = 'SettingsStorage'
    __cache_timeout__ = 10

    email_code_length = (
        'email_code_length',
        5,
        'Длина высылаемого EMAIL кода',
        int,
        None
    )

    service_url = (
        'service_url',
        'http://example.org',
        'URL',
        str,
        None,
    )

    uncached_value = (
        'uncached_value',
        5,
        'test',
        int,
        None,
        False
    )


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class AbstractSettingsValueTestCase(LambTestCase):

    @patch('lamb.ext.settings.AbstractSettingsValue._db_item')
    def test_cached_value_used(self, _db_item):
        SettingsValue.email_code_length._cached_item = AbstractSettingsStorage(value=314)
        assert cache.get('lamb_settings_email_code_length').value == 314
        assert SettingsValue.email_code_length.val == 314
        assert _db_item.call_count == 0

    @patch('lamb.ext.settings.AbstractSettingsValue._db_item', return_value=AbstractSettingsStorage(value=159))
    def test_cache_disabled_for_value(self, _db_item):
        SettingsValue.uncached_value._cached_item = AbstractSettingsStorage(value=314)
        assert not cache.get('lamb_settings_uncached_value')
        assert SettingsValue.uncached_value.val == 159
        assert _db_item.call_count == 1

    @patch('lamb.ext.settings.AbstractSettingsValue._db_item', return_value=AbstractSettingsStorage(value=159))
    def test_cached_value_updated_on_settings_change(self, _db_item):
        SettingsValue.email_code_length._cached_item = AbstractSettingsStorage(value=314)
        assert SettingsValue.email_code_length._cached_item
        assert cache.get('lamb_settings_email_code_length').value == 314

        SettingsValue.email_code_length.val = 159

        assert SettingsValue.email_code_length._cached_item.value == '159'
        assert cache.get('lamb_settings_email_code_length').value == '159'
        assert _db_item.call_count > 0

    @patch('lamb.ext.settings.AbstractSettingsValue._db_item')
    def test_cache_cleared(self, _db_item):
        cache.set('innocent_key', 'alive')
        SettingsValue.email_code_length._cached_item = AbstractSettingsStorage(value=314)
        SettingsValue.service_url._cached_item = AbstractSettingsStorage(value='example.org')
        assert cache.get('lamb_settings_email_code_length').value == 314
        assert cache.get('lamb_settings_service_url').value == 'example.org'

        assert SettingsValue.email_code_length._cached_item
        assert SettingsValue.service_url._cached_item

        SettingsValue.cache_clear()

        assert not SettingsValue.email_code_length._cached_item
        assert not SettingsValue.service_url._cached_item
        assert not cache.get('lamb_settings_email_code_length')
        assert not cache.get('lamb_settings_service_url')
        assert cache.get('innocent_key') == 'alive'
