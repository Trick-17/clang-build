from tqdm import tqdm as _tqdm
from colorama import Fore as _Fore

_MAX_DESCRIPTION_WIDTH = 16
_ELLIPSIS_WIDTH = 2
_BAR_FORMAT = "{desc: <%s}: {percentage:3.0f}%% |%s{bar}%s| {n_fmt: >5}/{total_fmt: >5} [{elapsed: >8}]" % (_MAX_DESCRIPTION_WIDTH, _Fore.BLUE, _Fore.RESET)


def _format_lenghty_string(text):
    if len(text) > _MAX_DESCRIPTION_WIDTH:
        return ((text[:-(_MAX_DESCRIPTION_WIDTH-_ELLIPSIS_WIDTH)] and '.' * _ELLIPSIS_WIDTH)
                + text[-(_MAX_DESCRIPTION_WIDTH-_ELLIPSIS_WIDTH):])
    else:
        return text


def _get_clang_build_progress_bar(iterable, disable, total):
    return _tqdm(iterable, bar_format=_BAR_FORMAT, leave=False, disable=disable, total=total)


class CategoryProgress:
    def __init__(self, categories, disable, total=None):
        self.pbar = _get_clang_build_progress_bar(categories, disable, total)
        self.current_catgeory = 0
        self.pbar.set_description_str(categories[self.current_catgeory])
        self.categories = categories
        self.index_limit = len(self.categories)

    def __enter__(self):
        self.entered_pbar = self.pbar.__enter__()
        return self

    def __exit__(self, type, value, traceback):
        self.entered_pbar.__exit__(type, value, traceback)

    def update(self):
        self.entered_pbar.update()
        self.current_catgeory += 1
        if self.current_catgeory >= self.index_limit:
            self.entered_pbar.set_description_str('Finished')
        else:
            self.entered_pbar.set_description_str(_format_lenghty_string(self.categories[self.current_catgeory]))

class IteratorProgress:
    def __init__(self, iterable, disable, total, access=lambda x: x):
        self.pbar = _get_clang_build_progress_bar(iterable, disable, total)
        self.access = access

    def __iter__(self):
        self.pbar_iter = self.pbar.__iter__()
        return self

    def __next__(self):
        val = self.pbar_iter.__next__()
        self.pbar.set_description_str(_format_lenghty_string(self.access(val)))
        return val

def get_build_progress_bar(iterable, disable, total, name):
    pbar = _get_clang_build_progress_bar(iterable, disable, total)
    pbar.set_description_str(_format_lenghty_string(name))
    return pbar
