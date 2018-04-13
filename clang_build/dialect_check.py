import subprocess as _subprocess
from functools import lru_cache as _lru_cache

_UNSUPPORTED_DIALECT_MESSAGE = "error: invalid value 'c++{0:02d}'"

def get_dialect_string(year):
    return '-std=c++{:02d}'.format(year)


def _check_dialect(year, clangpp):
    std_opt = get_dialect_string(year)
    try:
        _subprocess.run([clangpp, std_opt, '-x', 'c++', '-E', '-'],\
           check=True,input=b'',stdout=_subprocess.PIPE,stderr=_subprocess.PIPE)
    except _subprocess.CalledProcessError as e:
        error_message = _UNSUPPORTED_DIALECT_MESSAGE.format(year)
        strerr = e.stderr.decode('utf8','strict')
        if error_message in strerr:
            return False
        raise
    return True

@_lru_cache(maxsize=1)
def get_max_supported_compiler_dialect(clangpp):
    supported_dialects = []
    for dialect in range(30):
        if _check_dialect(dialect, clangpp):
            supported_dialects.append(dialect)

    if supported_dialects:
        return get_dialect_string(max(supported_dialects))
    else:
        return get_dialect_string(98)
