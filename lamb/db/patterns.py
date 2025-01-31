import enum

from django.conf import settings

from lamb.db.context import lamb_db_context
from lamb.db.session import DeclarativeBase
from lamb.exc import ServerError
from lamb.utils import get_primary_keys

__all__ = ["DbEnum", "ConfigEnum"]


def get_class_by_name(base, classname):
    """
    :param base: Declarative model base
    :param classname: SQLAlchemy Table name
    :return: Declarative class or None.
    """

    if not hasattr(base, "TABLES_BY_CLASS"):
        base.CLASSES_BY_NAME = {}
        for mapper in base.registry.mappers:
            cls = mapper.class_
            if not cls.__name__.startswith("_"):
                base.CLASSES_BY_NAME[cls.__name__] = cls

    return base.CLASSES_BY_NAME.get(classname, None)


@enum.unique
class DbEnum(enum.Enum):
    """Abstract enum to database processor.

    Abstract class that maps enum class to database table for store values.

    Example:

        import enum
        from lamb.db.patterns import DbEnum

        @enum.unique
        class TestPlain(DbEnum):
            value1 = 'value1'
            value2 = 'value2'
            value3 = 'value3'

            __table_class__ = '_TestPlainTable'

        class _TestPlainTable(DeclarativeBase):
            __tablename__ = 'test_plain'
            pk_code = Column(
                Enum(TestPlain),
                nullable=False,
                primary_key=True
            )

        TestPlain.value1.db_flush()
        print(TestPlain.value1)
    """

    __table_class__ = None
    __attrib_mapping__ = {}

    def __new__(cls, code, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = code
        return obj

    def _table_class(self):
        """
        :return: Database ORM table class
        :rtype: DeclarativeBase
        """
        if isinstance(self.__class__.__table_class__, str):
            return get_class_by_name(DeclarativeBase, self.__class__.__table_class__)
        elif isinstance(self.__class__.__table_class__, DeclarativeBase):
            return self.__class__.__table_class__
        else:
            raise ServerError(
                f"Improperly configured class {self.__class__.__name__}. Could not locate table class name"
            )

    def _setup_db_item(self, item):
        """Designed item initializer

        This method should be overridden in subclass if they have custom fields on database level.
        By default, method only assign primary key of underline table to value of self instance.

        :param item: Database table record instance
        :type item: lamb.db.session.DeclarativeBase
        :return: Initialized table record instance
        :rtype: lamb.db.session.DeclarativeBase
        """
        pk = get_primary_keys(item)
        pk_column_name, pk_column_description = pk.popitem()
        setattr(item, pk_column_name, self.value)
        return item

    def _db_item(self, session):
        """
        :param session: Databse session instance
        :type session: sqlalchemy.orm.Session
        :return: Initialized/extracted table record instance
        :rtype: lamb.db.session.DeclarativeBase
        """
        table_class = self._table_class()
        result = session.query(table_class).get(self.value)
        if result is None:
            result = table_class()
            self._setup_db_item(item=result)
            session.add(result)
            session.commit()
        return result

    @classmethod
    def db_map(cls, db_session):
        return {c: c._db_item(db_session) for c in cls}

    def db_flush(self):
        """
        :return: Explicitily flush enum value to database by touching it within session
        :rtype: None
        """
        with lamb_db_context(pooled=settings.LAMB_DB_CONTEXT_POOLED_SETTINGS) as session:
            _ = self._db_item(session)

    def __getattribute__(self, key):
        if key[:2] != "__":
            mapping = self.__class__.__attrib_mapping__
            if key in mapping:
                mapped_key = mapping[key]
                with lamb_db_context(pooled=settings.LAMB_DB_CONTEXT_POOLED_SETTINGS) as session:
                    db_item = self._db_item(session)
                    return getattr(db_item, mapped_key)
        return super().__getattribute__(key)

    def __setattr__(self, key, value):
        if key[:2] != "__":
            mapping = self.__class__.__attrib_mapping__
            if key in mapping:
                mapped_key = mapping[key]
                with lamb_db_context(pooled=settings.LAMB_DB_CONTEXT_POOLED_SETTINGS) as session:
                    db_item = self._db_item(session)
                    db_item.__setattr__(mapped_key, value)
                    session.commit()
        super().__setattr__(key, value)

    def __dir__(self):
        if isinstance(self.__class__.__attrib_mapping__, dict):
            return super().__dir__() + [str(k) for k in self.__class__.__attrib_mapping__]
        else:
            return super().__dir__()


@enum.unique
class ConfigEnum(DbEnum):
    """Config storage processor.

    Class that support store of values of enum in database.
    Support defaults/headers for each item that not stored in database

    Example:

        import enum
        from lamb.db.patterns import ConfigEnum

        @enum.unique
        class TestCode(ConfigEnum):
            Code1 = ('code1', 1, 'Header1')
            Code2 = ('code2', 2, 'Header2')
            Code3 = ('code3', 3, 'Header3')
            Code4 = ('code4', 4, 'Header4')
            Code5 = ('code5', 5, 'Header5')

            __table_class__ = '_TestCodeTable'
            __attrib_mapping__ = {'val':'value'}


        class _TestCodeTable(DeclarativeBase):
            __tablename__ = 'test_codes'
            code = Column(
                Enum(TestCode),
                nullable=False,
                primary_key=True,
                default=TestCode.Code1,
                server_default=TestCode.Code1.value
            )
            value = Column(INTEGER(unsigned=True), nullable=False)


        @enum.unique
        class TestSettings(ConfigEnum):
            settings1 = ('settings1',  1, 'ololo')
            settings2 = ('settings2',  2, 'ololo')
            settings3 = ('settings3',  3, 'ololo')

            __table_class__ = '_TestSettingsTable'
            __attrib_mapping__ = {'val':'value'}


        class _TestSettingsTable(DeclarativeBase):
            __tablename__ = 'test_settings'
            variable = Column(
                VARCHAR(50),
                nullable=False,
                primary_key=True
            )
            value = Column(
                VARCHAR(100),
                nullable=True
            )

        TestCode.Code1.val = 100
        TestSettings.settings1.val = 10

    """

    def __new__(cls, code, default, header, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.default = default
        obj.header = header
        return obj

    def _setup_db_item(self, item):
        item = super()._setup_db_item(item=item)
        item.value = self.default
        return item
