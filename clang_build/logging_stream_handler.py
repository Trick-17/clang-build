import logging as _logging
import tqdm as _tqdm

class TqdmHandler(_logging.StreamHandler):
    def __init__(self):
        _logging.StreamHandler.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        _tqdm.tqdm.write(msg)