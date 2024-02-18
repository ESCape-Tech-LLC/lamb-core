from __future__ import annotations

import time
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


__all__ = ["ExecutionTimeMeter"]


class ExecutionTimeMeter(object):
    """
    :type _markers: list[ExecutionTimeMeter.Marker]
    :type start_time: float
    :type context: Optional[list|tuple|set|dict]
    """

    class Marker(object):
        """
        :type message: str
        :type timestamp: float
        """

        def __init__(self, message=None):
            self.message = message
            self.timestamp = time.time()

    def __init__(self):
        # self._markers = list()
        # self.start_time = time.time()
        # self.context = None
        self.invalidate()

    def invalidate(self):
        self._markers = []
        self.start_time = time.time()
        self.context = None

    def append_marker(self, message: str = None):
        """Appends new marker to measures series"""
        self._markers.append(ExecutionTimeMeter.Marker(message))

    def get_total_time(self) -> float:
        """Total elapsed time interval"""
        return self._markers[len(self._markers) - 1].timestamp - self.start_time

    def get_measurements(self) -> List[Tuple[str, float, float, float]]:
        """List of measured values - tuple (message, absolute, relative, percentage)"""

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

    def get_log_messages(self, header: str = None):
        total_elapsed = self.get_total_time()
        measurements = self.get_measurements()

        message_elements = list()
        if isinstance(header, str):
            final_header = header + " measures: "
        else:
            final_header = "Time measures: "
        message_elements.append(final_header)
        message_elements.append(f"Total time: {total_elapsed:.6f} sec.")

        # print values
        for m in measurements:
            message_elements.append(f"\t{m[0]}: {m[2]:.6f} sec. [{m[3]:.2f} %%] ({m[1]:.6f} sec.)")

        return message_elements

    def log_marks(self, header: str = None):
        """Log collected markers using standard logging module"""
        try:
            message_elements = self.get_log_messages(header)
            message = "\n".join(message_elements)
            logger.info(message)
        except Exception:
            pass
