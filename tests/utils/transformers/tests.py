import datetime
import random

from lamb.utils import TZ_MSK, TZ_UTC
from lamb.utils.transformers import transform_datetime_tz

from tests.testcases import LambTestCase



class TestDatetimeTransformer(LambTestCase):
    def test_datetime_tz_transformer(self):
        current_datetime = datetime.datetime(
            year=random.randint(1900, 2025),
            month=random.randint(1, 12),
            day=random.randint(1, 28),
            hour=random.randint(1, 23),
            minute=random.randint(1, 59),
            second=random.randint(1, 59),
            microsecond=random.randint(1, 999999),
        )
        for test_data, starting_timezone, convert_timezone, expected in [
            (current_datetime, None, None, current_datetime),
            (current_datetime, TZ_MSK, None, current_datetime.astimezone(TZ_MSK).replace(tzinfo=None)),
            (current_datetime, TZ_UTC, TZ_MSK, current_datetime.astimezone(tz=TZ_MSK)),
            (current_datetime, None, TZ_MSK, current_datetime.replace(tzinfo=TZ_MSK)),
        ]:
            data = test_data
            if starting_timezone is not None:
                data = test_data.astimezone(starting_timezone)
            result = transform_datetime_tz(data, tz_info=convert_timezone)
            assert result == expected, test_data
