import sys
from unittest.mock import MagicMock

# Stub transient network-blocked sub-dependencies for offline / isolated environments
for mod in [
    "multidict",
    "propcache",
    "propcache.api",
]:
    if mod not in sys.modules:
        m = MagicMock()
        m.istr = str
        m.under_cached_property = property
        sys.modules[mod] = m
