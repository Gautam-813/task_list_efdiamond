from fastapi.templating import Jinja2Templates


class _SafeCache:
    def get(self, key, default=None):
        try:
            hash(key)
        except TypeError:
            return default
        return self._data.get(key, default) if hasattr(self, '_data') else default

    def __setitem__(self, key, value):
        try:
            hash(key)
        except TypeError:
            return
        if not hasattr(self, '_data'):
            self._data = {}
        self._data[key] = value

    def __contains__(self, item):
        try:
            hash(item)
        except TypeError:
            return False
        return item in getattr(self, '_data', {})


templates = Jinja2Templates(directory="app/templates")
templates.env._cache = _SafeCache()
