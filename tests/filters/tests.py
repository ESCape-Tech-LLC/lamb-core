from tests.testcases import LambTestCase
import sqlalchemy
from sqlalchemy.orm.query import Query

from lamb.db.session import DeclarativeBase
from lamb.utils.filters import FieldValueFilter


class Actor(DeclarativeBase):
    __tablename__ = 'actor'

    actor_id = sqlalchemy.Column(sqlalchemy.SMALLINT, primary_key=True)


class FieldValueFilterTestCase(LambTestCase):

    def test_comare_is_allowed(self):
        for compare in '__eq__', '__ne__', '__gt__', '__ge__', '__lt__', '__le__':
            with self.subTest(compare):
                FieldValueFilter('actor_id', str, Actor.actor_id, allowed_compares=[compare])

    def test_comare_is_applied(self):
        for compare, param, operator in [
                ('__gt__', 'actor_id.greater', '>'),
                ('__lt__', 'actor_id.less', '<'),
        ]:
            with self.subTest(compare):
                value_filter = FieldValueFilter('actor_id', str, Actor.actor_id, allowed_compares=[compare])
                result = value_filter.apply_to_query(Query(Actor), {param: 0})
                assert f"WHERE actor.actor_id {operator} %(actor_id_1)s" in str(result)
