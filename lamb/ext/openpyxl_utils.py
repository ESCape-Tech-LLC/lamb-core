# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import openpyxl


from typing import Optional, List, Generator, Tuple, Dict, Union, Callable
from openpyxl.cell import Cell as OpenpyxlCell
from openpyxl.worksheet import Worksheet as OpenpyxlWorksheet
from openpyxl.workbook import Workbook as OpenpyxlWorkbook

from lamb.exc import InvalidParamTypeError, InvalidParamValueError, ApiError, InvalidBodyStructureError


__all__ = ['Worksheet', 'Workbook', 'Cell', 'Row']


from collections import OrderedDict
logger = logging.getLogger(__name__)


""" 
Column names based wrapper around Excel worksheet

- use zero-based indexes instead of default openpyxl mode
"""

class Workbook(object):
    def __init__(self, filename, create_columns: bool = True):
        self._workbook = openpyxl.load_workbook(filename, data_only=True)
        self._create_columns = create_columns
        self._filename = filename

    @property
    def worksheets(self) -> List['Worksheet']:
        return [
            Worksheet(wrapped_worskheet=w, create_columns=self._create_columns)
            for w in self._workbook.worksheets
        ]

    # excel general
    @property
    def filename(self) -> str:
        return self._filename

    @property
    def openpyxl_workbook(self) -> OpenpyxlWorkbook:
        return self._workbook

    # iterators
    def iter_rows(self) -> Generator[Generator['Cell', None, None], None, None]:
        max_row = self._worksheet.max_row - 1
        for row in range(0, max_row):
            yield self.cells(row=row)

    def save(self, outputfile_path: str = None):
        if outputfile_path is None:
            outputfile_path = self._filename
        self._workbook.save(outputfile_path)


class Worksheet(object):
    _wrapped_worksheet: OpenpyxlWorksheet
    _create_columns: bool

    def __init__(self, wrapped_worskheet, create_columns):
        self._wrapped_worksheet = wrapped_worskheet
        self._create_columns = create_columns

    @property
    def openpyxl_worksheet(self) -> OpenpyxlWorksheet:
        return self._wrapped_worksheet

    @property
    def headers(self) -> List[Optional[str]]:
        return [cell.typed_value(req_type=str, default=None) for cell in self.cells(0)]

    @property
    def rows(self) -> Generator['Row', None, None]:
        max_row = self._wrapped_worksheet.max_row
        for row_index in range(0, max_row):
            yield Row(worksheet=self, row_index=row_index)

    # cell access
    def cells(self, row: int) -> Generator['Cell', None, None]:
        max_column = self._wrapped_worksheet.max_column
        for column in range(1, max_column + 1):
            result_cell = Cell(self._wrapped_worksheet.cell(row=row + 1, column=column))
            yield result_cell

    def cell(self, row: int, column: Union[int, str]) -> 'Cell':
        # check params
        if isinstance(column, str):
            column_index = self.column_index(column)
            if column_index is None:
                if self._create_columns:
                    max_column = self._wrapped_worksheet.max_column
                    self._wrapped_worksheet.cell(row=1, column=max_column + 1).value = column
                    column_index = max_column
                else:
                    raise InvalidParamValueError(f'Column with name={column} not exist')
        elif isinstance(column, int):
            column_index = column
        else:
            raise InvalidParamTypeError('Invalid value of column param')

        if not isinstance(row, int):
            raise InvalidParamTypeError('Invalid value of row param')
        else:
            row_index = row

        # extract value - openpyxl use 1-based indexs
        openpyxl_cell = self._wrapped_worksheet.cell(row=row_index + 1, column=column_index + 1)
        return Cell(cell=openpyxl_cell)

    # utilities
    def column_name(self, column_index) -> Optional[str]:
        _headers = self.headers
        if column_index < len(_headers):
            return _headers[column_index]
        else:
            return None

    def column_index(self, column_name: str) -> Optional[int]:
        _headers = self.headers
        if column_name in _headers:
            return _headers.index(column_name)
        else:
            return None




class Row(object):

    def __init__(self, worksheet: Worksheet, row_index: int):
        self._worksheet = worksheet
        self._row_index = row_index

    def __getitem__(self, column_name) -> 'Cell':
        return self._worksheet.cell(row=self._row_index, column=column_name)

    def __setitem__(self, column_name, value):
        self._worksheet.cell(row=self._row_index, column=column_name).value = value

    def cells(self) -> Generator['Cell', None, None]:
        max_column = self._worksheet.openpyxl_worksheet.max_column
        for column_index in range(0, max_column - 1):
            yield self._worksheet.cell(row=self._row_index, column=column_index)


class Cell(object):

    def __init__(self, cell: OpenpyxlCell):
        self._cell = cell

    def typed_value(self, req_type: type, allow_none: bool = False, transform: Callable = None, **kwargs):
        def _type_convert(_result):
            if req_type is None:
                return _result
            if isinstance(_result, req_type):
                return _result
            try:
                _result = req_type(_result)
                return _result
            except (ValueError, TypeError) as _e:
                raise InvalidParamTypeError('Invalid data type for value in cell') from _e

        try:
            # get and normalize value
            result = self._cell.value
            if len(str(result)) == 0:
                result = None

            # check none
            if result is None:
                if allow_none:
                    return None
                else:
                    raise InvalidParamTypeError('Invalid data type for value in cell')

            # apply type convert
            result = _type_convert(result)

            # apply transform
            if transform is not None:
                return transform(result)

            return result
        except Exception as e:
            if 'default' in kwargs.keys():
                return kwargs['default']
            elif isinstance(e, ApiError):
                raise
            else:
                raise InvalidBodyStructureError('Failed to parse cell value') from e

    @property
    def openpyxl_cell(self) -> OpenpyxlCell:
        return self._cell

    @property
    def value(self):
        return self.typed_value(req_type=str, allow_none=True)

    @value.setter
    def value(self, value):
        self._cell.value = value
