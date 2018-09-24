from enum import Enum as _Enum

class BuildType(_Enum):
    Default        = 'default'
    Release        = 'release'
    RelWithDebInfo = 'relwithdebinfo'
    Debug          = 'debug'
    Coverage       = 'coverage'

    def __str__(self):
        return self.value

    # Let's be case insensitive
    @classmethod
    def _missing_(cls, value):
        for item in cls:
            if item.value.lower() == value.lower():
                return item
        return super()._missing_(value)
