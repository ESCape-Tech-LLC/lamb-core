__author__ = 'KoNEW'
#-*- coding: utf-8 -*-

import time
import logging
logger = logging.getLogger(__name__)

__all__ = [
    'ExecutionTimeMeter'
]

class ExecutionTimeMeter(object):
    """
    :type _markers: list[ExecutionTimeMeter.Marker]
    :type start_time: float
    """

    class Marker(object):
        """
        :type message: unicode | None
        :type timestamp: float
        """
        def __init__(self, message = None):
            self.message = message
            self.timestamp = time.time()

    def  __init__(self):
        self._markers = list()
        self.start_time = time.time()

    def append_marker(self, message=None):
        """ Appends new marker to measures series
        :param message: String message to append to marker
        :type message: basestring
        """
        self._markers.append(ExecutionTimeMeter.Marker(message))


    def get_total_time(self):
        """
        :return: Total elapsed time interval
        :rtype: float
        :raises IndexError: In case of null count of records
        """
        return self._markers[len(self._markers) - 1].timestamp - self.start_time

    def get_measurements(self):
        """
        :return: List of measured values - tuple (message, absolute, relative, percentage)
        :rtype: list( (unicode, float, float, float) )
        :raises IndexError: In case of null count of records
        """

        total_elapsed = self.get_total_time()

        result = list()

        previous_timestamp = self.start_time
        for marker in self._markers:
            elapsed_absolute = marker.timestamp - self.start_time
            elapsed_relative = marker.timestamp - previous_timestamp
            percentage = elapsed_relative / total_elapsed * 100
            m = (marker.message, elapsed_absolute, elapsed_relative, percentage)
            result.append(m)
            previous_timestamp = marker.timestamp
        return result


    def log_marks(self, header=None):
        try:
            total_elapsed = self.get_total_time()
            measurements = self.get_measurements()

            message_elements = list()
            if isinstance(header, str):
                final_header =  header + ' measures: '
            else:
                final_header = 'Time measures: '
            message_elements.append(final_header)
            message_elements.append('Total time: %.6f sec.' % total_elapsed)

            # print values
            for m in measurements:
                message_elements.append('\t%s: %.6f sec. [%.2f %%] (%.6f sec.)' % (m[0], m[2], m[3], m[1]))
            message = '\n'.join(message_elements)
            logger.info(message)
        except:
            pass
