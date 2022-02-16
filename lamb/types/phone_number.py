# # -*- coding: utf-8 -*-
#
# import six
# from sqlalchemy import exc, types
#
# from lamb.exc import ImproperlyConfiguredError
# # from lamb.types.scalar_coercible import ScalarCoercible
# from sqlalchemy_utils.types.scalar_coercible import ScalarCoercible
# from lamb.utils import str_coercible
#
# try:
#     import phonenumbers
#     from phonenumbers.phonenumber import PhoneNumber as BasePhoneNumber
#     from phonenumbers.phonenumberutil import NumberParseException
# except ImportError:
#     phonenumbers = None
#     BasePhoneNumber = object
#     NumberParseException = Exception
#
#
# __all__ = ['PhoneNumber', 'PhoneNumberType']
#
#
# class PhoneNumberParseException(NumberParseException, exc.DontWrapMixin):
#     """
#     Wraps exceptions from phonenumbers with SQLAlchemy's DontWrapMixin
#     so we get more meaningful exceptions on validation failure instead of the
#     StatementException
#
#     Clients can catch this as either a PhoneNumberParseException or
#     NumberParseException from the phonenumbers library.
#     """
#     pass
#
#
# @str_coercible
# class PhoneNumber(BasePhoneNumber):
#     """
#     Extends a PhoneNumber class from `Python phonenumbers library`_. Adds
#     different phone number formats to attributes, so they can be easily used
#     in templates. Phone number validation method is also implemented.
#
#     Takes the raw phone number and country code as params and parses them
#     into a PhoneNumber object.
#     """
#     def __init__(self, raw_number, region=None, check_region=True):
#         # Bail if phonenumbers is not found.
#         if phonenumbers is None:
#             raise ImproperlyConfiguredError(
#                 "'phonenumbers' is required to use 'PhoneNumber'"
#             )
#
#         try:
#             self._phone_number = phonenumbers.parse(
#                 raw_number,
#                 region,
#                 _check_region=check_region
#             )
#         except NumberParseException as e:
#             # Wrap exception so SQLAlchemy doesn't swallow it as a
#             # StatementError
#             #
#             # Worth noting that if -1 shows up as the error_type
#             # it's likely because the API has changed upstream and these
#             # bindings need to be updated.
#             raise PhoneNumberParseException(
#                 getattr(e, 'error_type', -1),
#                 six.text_type(e)
#             )
#
#         super(PhoneNumber, self).__init__(
#             country_code=self._phone_number.country_code,
#             national_number=self._phone_number.national_number,
#             extension=self._phone_number.extension,
#             italian_leading_zero=self._phone_number.italian_leading_zero,
#             raw_input=self._phone_number.raw_input,
#             country_code_source=self._phone_number.country_code_source,
#             preferred_domestic_carrier_code=(
#                 self._phone_number.preferred_domestic_carrier_code
#             )
#         )
#         self.region = region
#         self.national = phonenumbers.format_number(
#             self._phone_number,
#             phonenumbers.PhoneNumberFormat.NATIONAL
#         )
#         self.international = phonenumbers.format_number(
#             self._phone_number,
#             phonenumbers.PhoneNumberFormat.INTERNATIONAL
#         )
#         self.e164 = phonenumbers.format_number(
#             self._phone_number,
#             phonenumbers.PhoneNumberFormat.E164
#         )
#
#     def __composite_values__(self):
#         return self.national, self.region
#
#     def is_valid_number(self):
#         return phonenumbers.is_valid_number(self._phone_number)
#
#     def __unicode__(self):
#         return self.national
#
#     def __hash__(self):
#         return hash(self.e164)
#
#
# class PhoneNumberType(types.TypeDecorator, ScalarCoercible):
#     """
#     Changes PhoneNumber objects to a string representation on the way in and
#     changes them back to PhoneNumber objects on the way out. If E164 is used
#     as storing format, no country code is needed for parsing the database
#     value to PhoneNumber object.
#     """
#
#     STORE_FORMAT = 'e164'
#     impl = types.Unicode(20)
#     python_type = PhoneNumber
#
#     def __init__(self, region='US', max_length=20, *args, **kwargs):
#         # Bail if phonenumbers is not found.
#         if phonenumbers is None:
#             raise ImproperlyConfiguredError(
#                 "'phonenumbers' is required to use 'PhoneNumberType'"
#             )
#
#         super(PhoneNumberType, self).__init__(*args, **kwargs)
#         self.region = region
#         self.impl = types.Unicode(max_length)
#
#     def process_bind_param(self, value, dialect):
#         if value:
#             if not isinstance(value, PhoneNumber):
#                 value = PhoneNumber(value, region=self.region)
#
#             if self.STORE_FORMAT == 'e164' and value.extension:
#                 return '%s;ext=%s' % (value.e164, value.extension)
#
#             return getattr(value, self.STORE_FORMAT)
#
#         return value
#
#     def process_result_value(self, value, dialect):
#         if value:
#             return PhoneNumber(value, self.region)
#         return value
#
#     def _coerce(self, value):
#         if value and not isinstance(value, PhoneNumber):
#             value = PhoneNumber(value, region=self.region)
#
#         return value or None
#
#     def process_literal_param(self, value, dialect):
#         return str(value)
