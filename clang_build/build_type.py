from enum import Enum as _Enum


class BuildType(_Enum):
    """Enumeration of all build types.

    Construction is case sensitive, i.e.

        >>> BuildType("default") == BuildType("Default")
        True

    """

    Default = "default"
    Release = "release"
    RelWithDebInfo = "relwithdebinfo"
    Debug = "debug"
    Coverage = "coverage"

    def __str__(self):
        """Return the value of the BuildType."""
        return self.value

    # Let's be case insensitive
    @classmethod
    def _missing_(cls, value):
        """Check for identical value except for caseing."""
        for item in cls:
            if item.value.lower() == value.lower():
                return item
        return super()._missing_(value)
