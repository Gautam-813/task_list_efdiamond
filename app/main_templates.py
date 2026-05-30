from fastapi.templating import Jinja2Templates


class _SafeCache:
    def get(self, key, default=None):
        try:
            hash(key)
        except TypeError:
            return default
        return getattr(self, '_mapping', {}).get(key, default)

    def __setitem__(self, key, value):
        try:
            hash(key)
        except TypeError:
            return
        if not hasattr(self, '_mapping'):
            self._mapping = {}
        self._mapping[key] = value

    def __contains__(self, item):
        try:
            hash(item)
        except TypeError:
            return False
        return item in getattr(self, '_mapping', {})


templates = Jinja2Templates(directory="app/templates")
env = templates.env
# Force-replace underlying cache objects to prevent unhashable key errors
for attr in ('cache', '_cache'):
    try:
        object.__setattr__(env, attr, _SafeCache())
    except (AttributeError, TypeError):
        pass
