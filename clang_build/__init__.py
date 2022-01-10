from pbr.version import VersionInfo as _VersionInfo
_v = _VersionInfo('clang-build').semantic_version()
__version__ = _v.release_string()
version_info = _v.version_tuple