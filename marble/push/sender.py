# # -*- coding: utf-8 -*-
# __author__ = 'KoNEW'
#
# from django.conf import settings
#
# from apns import APNs, Payload
# from gcm import GCM
#
# from pynm.push.device import (
#     NMMobileDevice,
#     ENVIRONMENT_SANDBOX,
#     PLATFORM_IOS,
#     PLATFORM_ANDROID
# )
# from pynm.db.session import marble_db_session_maker
#
# class PushSender(object):
#
#     def __init__(self):
#         # APNs sandbox
#         self.apns_sandbox = APNs(
#             use_sandbox=True,
#             cert_file=settings.MARBLE_APNS_CERT_SANDBOX,
#             key_file=settings.MARBLE_APNS_CERT_SANDBOX,
#             enhanced=True
#         )
#         self.apns_sandbox.gateway_server.register_response_listener(self._apns_response_listener)
#
#         # APNs production
#         self.apns_production = APNs(
#             use_sandbox=False,
#             cert_file=settings.MARBLE_APNS_CERT_PRODUCTION,
#             key_file=settings.MARBLE_APNS_CERT_PRODUCTION,
#             enhanced=True
#         )
#         self.apns_production.gateway_server.register_response_listener(self._apns_response_listener)
#
#         # APNs packages to handle errors
#         self.apns_packages = dict()
#         # """ :type apns_packages: list[MobileDeviceIos]"""
#
#         # Configure GCM
#         self.gcm = GCM(settings.MARBLE_GOOGLE_PLAY_GCM_API_KEY)
#
#         # configure database session
#         self.db_session = marble_db_session_maker()
#
#     def _apns_response_listener(self, error_response):
#         if self.db_session is not None:
#             status_code = error_response['status']
#             apns_identifier = error_response['identifier']
#             if status_code == 8 and apns_identifier in self.apns_packages.keys():
#                 ios_device = self.apns_packages[apns_identifier]
#                 self.db_session.delete(ios_device)
#                 self.db_session.commit()
#                 print 'Did delete APNs device: ', ios_device.token
#
#
#     def send_notification(self, devices, message="", payload_data=None, badge_number=None):
#         """
#         :param devices: Array of devices to send notification
#         :type devices: list[NMMobileDevice]
#         :param message: Push alert message
#         :type message: basestring
#         :param payload_data: Push payload data
#         :type payload_data: dict
#         :param badge_number: Push badge number
#         :type badge_number: int
#         """
#         ios_devices = [d for d in devices if d.platform == PLATFORM_IOS]
#         """ :type ios_devices: list[MobileDeviceIos] """
#         android_devices = [d for d in devices if d.platform == PLATFORM_ANDROID]
#         """ :type android_devices: list[MobileDeviceAndroid] """
#
#         print "Devices: \niOS:%s \nAndroid:%s" % (ios_devices, android_devices)
#
#         # send ios data
#         apns_payload = Payload(alert=message, sound='default', badge=badge_number, custom=payload_data)
#         apns_identifier = 0
#         for d in ios_devices:
#             apns_identifier += 1
#             self.apns_packages[apns_identifier] = d
#             try:
#                 if d.environment == ENVIRONMENT_SANDBOX:
#                     server = self.apns_sandbox.gateway_server
#                 else:
#                     server = self.apns_production.gateway_server
#                 server.send_notification(token_hex=d.token, payload=apns_payload, identifier=apns_identifier)
#                 print "Did send APNs push: ", d.token
#             except Exception as e:
#                 print 'Unhandled APNs error: %s' % e
#
#         # send GCM data
#         if len(android_devices) > 0:
#             gcm_payload = payload_data
#             gcm_payload['message'] = message
#             gcm_payload['badge_number'] = badge_number
#             gcm_reg_ids = [d.token for d in android_devices]
#             response = self.gcm.json_request(registration_ids=gcm_reg_ids, data=gcm_payload)
#             if 'errors' in response:
#                 for error, reg_ids in response['errors'].items():
#                     if error in ['MismatchSenderId', 'NotRegistered', 'InvalidRegistration']:
#                         if self.db_session is not None:
#                             devices_to_remove = [d for d in android_devices if d.token in reg_ids]
#                             for d in devices_to_remove:
#                                 self.db_session.delete(d)
#                             self.db_session.commit()
#                             print 'Did delete GCM devices: ', [d.token for d in devices_to_remove]
#                     else:
#                         print 'Unhandled GCM error: %s for reg_ids=%s' % (error, reg_ids)
#             else:
#                 print "Did send Android notifications: ", [a.token for a in android_devices]
#
#             # handle canonical changes
#             if 'canonical' in response and self.db_session is not None:
#                 for reg_id, canonical_id in response['canonical'].items():
#                     for d in android_devices:
#                         if d.token == reg_id:
#                             d.token = canonical_id
#                             break
#                 self.db_session.commit()
