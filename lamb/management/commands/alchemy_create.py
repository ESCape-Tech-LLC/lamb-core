import warnings

from lamb.management.commands.lamb_alchemy_create import Command as NewCommand

warnings.warn("alchemy_create is deprecated, use lamb_alchemy_create instead", DeprecationWarning)

Command = NewCommand
