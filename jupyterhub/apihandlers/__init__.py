from .base import *
from .auth import *
from .hub import *
from .proxy import *
from .users import *
from .cityscope import *

from . import auth, hub, proxy, users, cityscope

default_handlers = []
for mod in (auth, hub, proxy, users, cityscope):
    default_handlers.extend(mod.default_handlers)
