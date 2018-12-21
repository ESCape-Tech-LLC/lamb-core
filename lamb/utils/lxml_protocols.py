# -*- coding: utf-8 -*-

import enum

from datetime import datetime, date


# utilities
def __add_numeric__(elem, item):
    elem.text = str(item)


def __add_boolean__(elem, item):
    if item:
        elem.text = 'true'
    else:
        elem.text = 'false'


def __add_enum__(elem, item):
    elem.text = str(item.value)


def __add_string__(elem, item):
    elem.text = item


def __add_datetime__(elem, item):
    elem.text = item.strftime('%Y-%m-%d %H:%M:%S')


def __add_date__(elem, item):
    elem.text = item.strftime('%Y-%m-%d')


def __add_none__(_, __):
    pass


__lxml_mapping__ = {
    int:            (__add_numeric__, 'integer'),
    float:          (__add_numeric__, 'float'),
    bool:           (__add_boolean__, 'boolean'),
    str:            (__add_string__, 'string'),
    datetime:       (__add_datetime__, 'string'),
    date:           (__add_date__, 'string'),
    enum.IntEnum:   (__add_enum__, 'integer'),
    enum.Enum:      (__add_enum__, 'string'),
    type(None):     (__add_none__, 'string')
}


__lxml_types_map__ = {k: v[0] for k, v in __lxml_mapping__.items()}
__lxml_hints_map__ = {k: v[1] for k, v in __lxml_mapping__.items()}
__lxml_hints_reverse_map__ = {v[1]: k for k, v in __lxml_mapping__.items() if k in [int, float, bool, str]}
