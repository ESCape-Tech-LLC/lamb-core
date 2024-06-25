import os
import json
from datetime import date
from functools import partial

from django.conf import settings

# Lamb Framework
from lamb import exc
from lamb.utils import dpath_value
from lamb.utils.dpath import adapt_dict_impl

# noinspection PyUnresolvedReferences
from lxml import etree
from tests.testcases import LambTestCase

DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DOC = json.load(open(os.path.join(DIR, "fixture.json")))
XML_DOC = etree.parse(open(os.path.join(DIR, "fixture.xml")))


class DictionaryTestMixin:
    _engine: str = None

    @classmethod
    def setUpClass(cls):
        print("\n")
        settings.LAMB_DPATH_DICT_ENGINE = cls._engine
        adapt_dict_impl()
        print(f"testing: {cls._engine} -> {settings.LAMB_DPATH_DICT_ENGINE}")

    def test_simple_path(self):
        self.assertEqual(dpath_value(JSON_DOC, ["actors", "actor", 1, "character", 0]), "Sir Robin")

    def test_none_val(self):
        self.assertEqual(dpath_value(JSON_DOC, ["actors", "actor", 1, "none-val"], allow_none=True), None)

    def test_disallowed_none_raises(self):
        with self.assertRaises(exc.InvalidParamTypeError):
            dpath_value(JSON_DOC, ["actors", "actor", 1, "none-val"], req_type=str, allow_none=False)

    def test_not_found_raises(self):
        with self.assertRaises(exc.InvalidBodyStructureError):
            dpath_value(JSON_DOC, ["actors", "bad_actor", 1, "character", 0])

    def test_not_found_default(self):
        self.assertEqual(dpath_value(JSON_DOC, ["actors", "bad_actor", 1, "character", 0], default=10), 10)

    def test_bad_dpath_type_raises(self):
        with self.assertRaises(exc.ServerError):
            dpath_value(JSON_DOC, None)

    def test_reqtype(self):
        self.assertEqual(
            dpath_value(JSON_DOC, ["actors", "actor", 1, "character", 0], req_type=frozenset), frozenset("Sir Robin")
        )

    def test_invalid_reqtype_raises(self):
        with self.assertRaises(exc.InvalidParamTypeError):
            dpath_value(JSON_DOC, ["actors", "actor", 1, "character", 0], req_type=int)

    def test_transformers(self):
        # Lamb Framework
        from lamb.utils import transformers

        # Datetime (?)
        self.assertEqual(
            dpath_value(JSON_DOC, "date", transform=partial(transformers.transform_date, __format="%Y-%m-%d")),
            date(2017, 4, 20),
        )

        # Boolean
        self.assertEqual(dpath_value(JSON_DOC, "boolean1", transform=transformers.transform_boolean), True)
        self.assertEqual(dpath_value(JSON_DOC, "boolean0", transform=transformers.transform_boolean), False)
        self.assertEqual(dpath_value(JSON_DOC, "true", transform=transformers.transform_boolean), True)
        self.assertEqual(dpath_value(JSON_DOC, "booleanTrue", transform=transformers.transform_boolean), True)
        self.assertEqual(dpath_value(JSON_DOC, "booleanFALSE", transform=transformers.transform_boolean), False)

        # Enum
        import enum

        @enum.unique
        class StringEnum(str, enum.Enum):
            FIRST = "first"
            SECOND = "second"

        self.assertEqual(
            dpath_value(
                JSON_DOC, "enum_first", transform=partial(transformers.transform_string_enum, enum_class=StringEnum)
            ),
            StringEnum.FIRST,
        )

        self.assertEqual(
            dpath_value(
                JSON_DOC, "enum_second", transform=partial(transformers.transform_string_enum, enum_class=StringEnum)
            ),
            StringEnum.SECOND,
        )

        # Enum with default and allow_none
        self.assertEqual(
            dpath_value(
                JSON_DOC,
                "enum_second",
                transform=partial(transformers.transform_string_enum, enum_class=StringEnum),
                default=None,
                allow_none=True,
            ),
            StringEnum.SECOND,
        )

        # Enum with default and allow_none (return default)
        self.assertEqual(
            dpath_value(
                JSON_DOC,
                "no-such-key",
                transform=partial(transformers.transform_string_enum, enum_class=StringEnum),
                default=5,
                allow_none=True,
            ),
            5,
        )

        # UUID
        import uuid

        self.assertEqual(
            dpath_value(JSON_DOC, "uuid", transform=transformers.transform_uuid),
            uuid.UUID("2752051C-1EEA-4B8C-A29C-A9C72B7DB727"),
        )


class DpathTest(DictionaryTestMixin, LambTestCase):
    _engine = "dpath"


class ReduceTest(DictionaryTestMixin, LambTestCase):
    _engine = "reduce"


class EtreeTestCase(LambTestCase):
    def test_simple_path_on_tree(self):
        self.assertEqual(dpath_value(XML_DOC, "actor[2]/character[1]"), "Sir Robin")

    def test_simple_path_on_element(self):
        self.assertEqual(dpath_value(XML_DOC.find("actor[2]"), "./character[1]"), "Sir Robin")

    def test_none_val(self):
        self.assertEqual(dpath_value(XML_DOC, "actor[2]/none-val", allow_none=True), None)

    def test_disallowed_none_raises(self):
        with self.assertRaises(exc.InvalidParamTypeError):
            dpath_value(XML_DOC, "actor[2]/none-val", req_type=str, allow_none=False)

    def test_not_found_raises(self):
        with self.assertRaises(exc.InvalidBodyStructureError):
            dpath_value(XML_DOC, "actor[1]/character[22]")

    def test_not_found_default(self):
        self.assertEqual(dpath_value(XML_DOC, "actor[1]/character[22]", default=10), 10)

    def test_bad_dpath_raises(self):
        with self.assertRaises(exc.ServerError):
            dpath_value(XML_DOC, None)

    def test_reqtype(self):
        self.assertEqual(dpath_value(XML_DOC, "actor[2]/character[1]", req_type=frozenset), frozenset("Sir Robin"))

    def test_invalid_reqtype_wo_default_raises(self):
        with self.assertRaises(exc.InvalidParamTypeError):
            dpath_value(XML_DOC, "actor[1]/character[1]", req_type=int)

    def test_auto_typehint(self):
        self.assertEqual(dpath_value(XML_DOC, "actor[1]/auto_bool"), True)
        self.assertEqual(dpath_value(XML_DOC, "actor[1]/auto_float"), 2.345)
        self.assertEqual(dpath_value(XML_DOC, "actor[1]/auto_integer"), 120)

    def test_transformers(self):
        # Lamb Framework
        from lamb.utils import transformers

        # Datetime (?)
        self.assertEqual(
            dpath_value(XML_DOC, "actor[1]/date", transform=partial(transformers.transform_date, __format="%Y-%m-%d")),
            date(2017, 4, 20),
        )

        # Boolean
        self.assertEqual(dpath_value(XML_DOC, "actor[1]/boolean1", transform=transformers.transform_boolean), True)
        self.assertEqual(dpath_value(XML_DOC, "actor[1]/boolean0", transform=transformers.transform_boolean), False)
        self.assertEqual(dpath_value(XML_DOC, "actor[1]/true", transform=transformers.transform_boolean), True)

        # Enum
        import enum

        @enum.unique
        class StringEnum(str, enum.Enum):
            FIRST = "first"
            SECOND = "second"

        self.assertEqual(
            dpath_value(
                XML_DOC,
                "actor[1]/enum_first",
                transform=partial(transformers.transform_string_enum, enum_class=StringEnum),
            ),
            StringEnum.FIRST,
        )

        self.assertEqual(
            dpath_value(
                XML_DOC,
                "actor[1]/enum_second",
                transform=partial(transformers.transform_string_enum, enum_class=StringEnum),
            ),
            StringEnum.SECOND,
        )

        # UUID
        import uuid

        self.assertEqual(
            dpath_value(XML_DOC, "actor[1]/uuid", transform=transformers.transform_uuid),
            uuid.UUID("2752051C-1EEA-4B8C-A29C-A9C72B7DB727"),
        )
