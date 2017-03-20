# # -*- coding: utf-8 -*-
# __author__ = 'KoNEW'
#
# from datetime import datetime
#
# from sqlalchemy import Column, text
# from sqlalchemy.dialects.mysql import VARCHAR, ENUM, TIMESTAMP
# from sqlalchemy.orm import validates
#
# from marble.db.session import DeclarativeBase
# from marble.db.mixins import TableConfigMixin
# from marble.rest.exceptions import *
#
#
# # Mobile platforms constants
# PLATFORM_IOS = 'ios'
# PLATFORM_ANDROID = 'android'
# PLATFORM_WINDOWS_PHONE = 'windows_phone'
# PLATFORM_UNKNOWN = 'unknown'
#
#
# # ENVIRONMENTS
# ENVIRONMENT_SANDBOX = 'sandbox'
# ENVIRONMENT_PRODUCTION = 'production'
#
#
# class NMMobileDevice(DeclarativeBase, TableConfigMixin):
#     __tablename__ = 'nm_mobile_device'
#
#     # columns
#     token = Column(VARCHAR(250), nullable=False, primary_key=True)
#     locale_iso_code = Column(VARCHAR(10), nullable=False, default='ru', server_default='ru')
#     time_created = Column(TIMESTAMP, nullable=False, default=datetime.now,
#                           server_default=text('CURRENT_TIMESTAMP'))
#     time_updated = Column(TIMESTAMP, nullable=False, default=datetime.now,
#                           server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
#     environment = Column(
#         ENUM(
#             ENVIRONMENT_SANDBOX,
#             ENVIRONMENT_PRODUCTION
#         ),
#         default=ENVIRONMENT_PRODUCTION,
#         server_default=ENVIRONMENT_PRODUCTION,
#         nullable=False
#     )
#
#     platform = Column(
#         ENUM(
#             PLATFORM_IOS,
#             PLATFORM_ANDROID,
#             PLATFORM_WINDOWS_PHONE,
#             PLATFORM_UNKNOWN
#         ),
#         default=PLATFORM_UNKNOWN,
#         server_default=PLATFORM_UNKNOWN,
#         primary_key=True,
#         nullable=False
#     )
#
#     # methods
#     @validates('environment')
#     def validate_latitude(self, key, value):
#         if value not in [ENVIRONMENT_PRODUCTION, ENVIRONMENT_SANDBOX]:
#             raise InvalidParamValueError('Invalid value for environment')
#         return value
#
#     @validates('platform')
#     def validate_platform(self, key, value):
#         print value
#         if value not in [PLATFORM_UNKNOWN, PLATFORM_IOS, PLATFORM_ANDROID, PLATFORM_WINDOWS_PHONE, None]:
#             raise InvalidParamValueError('Invalid device platform')
#         return value