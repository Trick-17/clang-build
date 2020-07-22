import logging as _logging
import tqdm as _tqdm

class TqdmHandler(_logging.StreamHandler):
    def __init__(self):
        _logging.StreamHandler.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        _tqdm.tqdm.write(msg)

class NamedLoggerAdapter(_logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return '%s: %s' % (self.extra['tree_element'].__str__(), msg), kwargs

class NamedLogger:
    def __init__(self, logger):
        self._logger = NamedLoggerAdapter(logger, {'tree_element': self})

    def log_message(self, message: str) -> str:
        """
        """
        return f"{self.__str__()}: {message}"
