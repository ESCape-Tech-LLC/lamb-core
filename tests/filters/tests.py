import re

import sqlalchemy
from sqlalchemy.orm.query import Query

from lamb.db.session import DeclarativeBase
from lamb.utils.filters import FieldValueFilter

from tests.testcases import LambTestCase


class Actor(DeclarativeBase):
    __tablename__ = 'actor'

    actor_id = sqlalchemy.Column(sqlalchemy.SMALLINT, primary_key=True)


class FieldValueFilterTestCase(LambTestCase):

    def test_compare_is_allowed(self):
        for compare in '__eq__', '__ne__', '__gt__', '__ge__', '__lt__', '__le__':
            with self.subTest(compare):
                FieldValueFilter('actor_id', str, Actor.actor_id, allowed_compares=[compare])

    def test_compare_is_applied(self):
        for compare, param, operator in [
                ('__gt__', 'actor_id.greater', '>'),
                ('__lt__', 'actor_id.less', '<'),
        ]:
            with self.subTest(compare):
                value_filter = FieldValueFilter('actor_id', str, Actor.actor_id, allowed_compares=[compare])
                result = value_filter.apply_to_query(Query(Actor), {param: 0})
                assert f"WHERE actor.actor_id {operator} %(actor_id_1)s" in str(result)

    def test_null_argument(self):
        for compare, param, operator in [
                ('__eq__', 'actor_id', 'IS NULL'),
                ('__ne__', 'actor_id.exclude', 'IS NOT NULL'),
        ]:
            with self.subTest(compare):
                value_filter = FieldValueFilter('actor_id', str, Actor.actor_id, allowed_compares=[compare])
                result = value_filter.apply_to_query(Query(Actor), {param: 'null'})
                assert f"WHERE actor.actor_id {operator}" in str(result)

    def test_null_argument_in_list(self):
        for compare, param, operator in [
            ('__eq__', 'actor_id',
             r'IN \((\[POSTCOMPILE_actor_id_1]|%\(actor_id_1\)s, %\(actor_id_2\)s)\) OR actor.actor_id IS NULL'),
            ('__ne__', 'actor_id.exclude',
             r'NOT IN \((\[POSTCOMPILE_actor_id_1]|%\(actor_id_1\)s, %\(actor_id_2\)s)\) AND actor.actor_id IS NOT '
             r'NULL'),
        ]:
            with self.subTest(compare):
                value_filter = FieldValueFilter('actor_id', str, Actor.actor_id, allowed_compares=[compare])
                result = value_filter.apply_to_query(Query(Actor), {param: '1,null,3'})
                assert re.search(r'WHERE actor.actor_id ' + operator, str(result)), str(result)
