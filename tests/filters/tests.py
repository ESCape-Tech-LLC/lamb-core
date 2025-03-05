import datetime
import random
import re

# SQLAlchemy
from sqlalchemy import delete, select
from sqlalchemy.orm.query import Query

from lamb.exc import ServerError
from tests.filters.model import DatetimeModel, Actor
from lamb.db.context import lamb_db_context

# Lamb Framework
from lamb.utils import TZ_UTC, TZ_MSK, response_filtered
from lamb.utils.filters import FieldValueFilter, DatetimeFilter

from tests.testcases import LambTestCase


class FieldValueFilterTestCase(LambTestCase):
    def test_compare_is_allowed(self):
        for compare in "__eq__", "__ne__", "__gt__", "__ge__", "__lt__", "__le__":
            with self.subTest(compare):
                FieldValueFilter("actor_id", str, Actor.actor_id, allowed_compares=[compare])

    def test_compare_is_applied(self):
        for compare, param, operator in [
            ("__gt__", "actor_id.greater", ">"),
            ("__lt__", "actor_id.less", "<"),
        ]:
            with self.subTest(compare):
                value_filter = FieldValueFilter("actor_id", str, Actor.actor_id, allowed_compares=[compare])
                result = value_filter.apply_to_query(Query(Actor), {param: 0})
                assert f"WHERE actor.actor_id {operator} %(actor_id_1)s" in str(result)

    def test_null_argument(self):
        for compare, param, operator in [
            ("__eq__", "actor_id", "IS NULL"),
            ("__ne__", "actor_id.exclude", "IS NOT NULL"),
        ]:
            with self.subTest(compare):
                value_filter = FieldValueFilter("actor_id", str, Actor.actor_id, allowed_compares=[compare])
                result = value_filter.apply_to_query(Query(Actor), {param: "null"})
                assert f"WHERE actor.actor_id {operator}" in str(result)

    def test_null_argument_in_list(self):
        for compare, param, operator in [
            (
                    "__eq__",
                    "actor_id",
                    r"IN \((\[POSTCOMPILE_actor_id_1]|%\(actor_id_1\)s, %\(actor_id_2\)s)\) OR actor.actor_id IS NULL",
            ),
            (
                    "__ne__",
                    "actor_id.exclude",
                    r"NOT IN \((\[POSTCOMPILE_actor_id_1]|%\(actor_id_1\)s, %\(actor_id_2\)s)\) AND actor.actor_id IS NOT "
                    r"NULL",
            ),
        ]:
            with self.subTest(compare):
                value_filter = FieldValueFilter("actor_id", str, Actor.actor_id, allowed_compares=[compare])
                result = value_filter.apply_to_query(Query(Actor), {param: "1,null,3"})
                assert re.search(r"WHERE actor.actor_id " + operator, str(result)), str(result)


class DatetimeFieldValueFilterTestCase(LambTestCase):
    def setup_init(self):
        test_datetime_1 = datetime.datetime(2020, 2, 1, hour=random.randint(1, 23), minute=random.randint(1, 59))
        self.test_datetime_2 = datetime.datetime(2020, 1, 5, hour=random.randint(1, 23), minute=random.randint(1, 59))
        test_datetime_3 = datetime.datetime(2020, 3, 10, hour=random.randint(1, 23), minute=random.randint(1, 59))
        test_datetime_4 = datetime.datetime(2020, 1, 10, hour=random.randint(1, 23), minute=random.randint(1, 59))
        self.test_datetime_tz_1 = test_datetime_1.astimezone(tz=TZ_UTC)
        test_datetime_tz_2 = self.test_datetime_2.astimezone(tz=TZ_MSK)
        test_datetime_tz_3 = test_datetime_3.astimezone(tz=TZ_MSK)
        self.test_datetime_tz_4 = test_datetime_4.astimezone(tz=TZ_UTC)

        test_instance_1 = DatetimeModel(record_datetime_tz=self.test_datetime_tz_1,
                                        record_datetime=test_datetime_1)
        test_instance_2 = DatetimeModel(record_datetime_tz=test_datetime_tz_2,
                                        record_datetime=self.test_datetime_2)
        test_instance_3 = DatetimeModel(record_datetime_tz=test_datetime_tz_3,
                                        record_datetime=test_datetime_3)
        test_instance_4 = DatetimeModel(record_datetime_tz=self.test_datetime_tz_4,
                                        record_datetime=test_datetime_4)

        with lamb_db_context() as session:
            session.execute(delete(DatetimeModel))
            session.add_all([test_instance_1, test_instance_2, test_instance_3, test_instance_4])
            session.commit()

    def test_filter_datetime_tz_ok(self):
        self.setup_init()
        with lamb_db_context() as session:
            filters = [
                DatetimeFilter(DatetimeModel.record_datetime_tz, fmt="iso")
            ]
            stmt = select(DatetimeModel).order_by(DatetimeModel.id)

            params = {"record_datetime_tz.max": self.test_datetime_tz_1.isoformat()}

            filtered_stmt = response_filtered(stmt, filters, params=params)
            result = session.execute(filtered_stmt).scalars().all()
            self.assertEqual(len(result), 3)

    def test_filter_datetime_incoming_tz_ok(self):
        self.setup_init()
        with lamb_db_context() as session:
            filters = [
                DatetimeFilter(DatetimeModel.record_datetime_tz, fmt="iso", tz_info=TZ_MSK, tz_strict=True)
            ]
            stmt = select(DatetimeModel).order_by(DatetimeModel.id)
            params = {"record_datetime_tz": self.test_datetime_tz_4.isoformat()}
            filtered_stmt = response_filtered(stmt, filters, params=params)
            result = session.execute(filtered_stmt).scalars().all()
            self.assertEqual(len(result), 1)

    def test_filter_datetime_tz_strict_error(self):
        self.setup_init()
        with self.assertRaises(ServerError):
            DatetimeFilter(DatetimeModel.record_datetime_tz, fmt="iso", tz_strict=True)


    def test_filter_datetime_ok(self):
        self.setup_init()
        with lamb_db_context() as session:
            filters = [
                DatetimeFilter(DatetimeModel.record_datetime, fmt="iso")
            ]
            stmt = select(DatetimeModel).order_by(DatetimeModel.id)

            params = {"record_datetime_tz.min": self.test_datetime_2.isoformat()}

            filtered_stmt = response_filtered(stmt, filters, params=params)
            result = session.execute(filtered_stmt).scalars().all()
            self.assertEqual(len(result), 4)

    def test_filter_datetime_strict_error(self):
        self.setup_init()
        with self.assertRaises(ServerError):
            DatetimeFilter(DatetimeModel.record_datetime, fmt="iso", tz_info=TZ_UTC, tz_strict=True)
