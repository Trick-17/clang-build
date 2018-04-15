from tqdm import tqdm as _tqdm
from colorama import Fore as _Fore

_MAX_DESCRIPTION_WIDTH = 16
_ELLIPSIS_WIDTH = 2


def _format_lenghty_string(text, max_width, ellipsis_width):
    if len(text) > max_width:
        return ((text[:-(max_width-ellipsis_width)] and '.' * ellipsis_width)
                + text[-(max_width-ellipsis_width):])
    else:
        return text

class CategoryIterator:
    '''
    Simple wrapper to change the description of the progress bar,
    whenever the next item is requested.
    '''
    def __init__(self, iterator, bar):
        self.iter = iterator
        self.bar = bar

    def __next__(self):
        self.bar._update_iter()
        return self.iter.__next__()

class BuildProgressBar(_tqdm):
    def __init__(self, disable, *args, **kwargs):
        super().__init__(
            *args,
            bar_format="{desc: <%s}: {percentage:3.0f}%% |%s{bar}%s| {n_fmt: >5}/{total_fmt: >5} [{elapsed: >8}]" % (_MAX_DESCRIPTION_WIDTH, _Fore.BLUE, _Fore.RESET),
            leave=False,
            disable=disable,
            **kwargs)

class CategoryProgressBar(BuildProgressBar):
    def __init__(self, categories, disable, access=lambda x: x):
        self.categories = [_format_lenghty_string(access(category), _MAX_DESCRIPTION_WIDTH, _ELLIPSIS_WIDTH) for category in categories]
        self.current_category = 0
        super().__init__(
            disable,
            categories)
        self._set_category()

    def _update_iter(self):
        self.current_category += 1
        self._set_category()

    def update(self, n=1):
        _tqdm.update(self, n)
        self._update_iter()

    def __iter__(self):
        self.current_category -= 1
        return CategoryIterator(_tqdm.__iter__(self), self)

    def _set_category(self):
        if self.current_category < len(self.categories):
            self.set_description_str(self.categories[self.current_category])
        else:
            self.set_description_str('finished.')


