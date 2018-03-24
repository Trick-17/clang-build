from pbr.version import VersionInfo

_v = VersionInfo('clang-build').semantic_version()
__version__ = _v.release_string()
version_info = _v.version_tuple