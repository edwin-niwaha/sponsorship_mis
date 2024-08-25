from sys import stdout

import colorama
from colorama import Fore, Style

from .settings import *  # noqa: F403

# colorama
colorama.init(autoreset=True)
stdout.write(
    f"{Fore.GREEN}{Style.BRIGHT}================ Loading Local Environment Variables =====================\n"  # noqa: E501
)

DEBUG = True


INSTALLED_APPS += [  # noqa: F405
    # ...
    "debug_toolbar",
    "django_browser_reload",
    # ...
]

MIDDLEWARE += [  # noqa: F405
    # ...
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    # ...
]

INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]
