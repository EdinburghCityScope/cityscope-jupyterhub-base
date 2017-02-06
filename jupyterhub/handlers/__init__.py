from .base import *
from .login import *

from . import base, pages, login, uploader

default_handlers = []
for mod in (base, pages, login, uploader):
    default_handlers.extend(mod.default_handlers)
