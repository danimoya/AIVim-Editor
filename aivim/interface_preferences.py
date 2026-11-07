"""Small user-wide UI preferences stored privately outside the repository."""
from .session import SessionStore


class InterfacePreferences:
    def __init__(self, config_path):
        self.store = SessionStore(config_path)
        self.store.path = self.store.path.with_name('preferences-' + self.store.path.name)

    def load(self):
        return (self.store.load() or {}).get('preferences', {})

    def update(self, values):
        preferences = self.load()
        preferences.update(values)
        self.store.save({'documents': [], 'preferences': preferences})
