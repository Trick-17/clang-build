from enum import Enum as _Enum

class BuildType(_Enum):
    Default        = 'default'
    Release        = 'release'
    #MinSizeRel     = 2
    #RelWithDebInfo = 3
    Debug          = 'debug'
    #Coverage       = 5

    def __str__(self):
        return self.value

    # Let's be case insensitive
    @classmethod
    def _missing_(cls, value):
        for item in cls:
            if item.value.lower() == value.lower():
                return item
        return super()._missing_(value)
