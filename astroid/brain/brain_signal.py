# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
"""Astroid hooks for the signal library.

The signal module generates the 'Signals', 'Handlers' and 'Sigmasks' IntEnums
dynamically using the IntEnum._convert() classmethod, which modifies the module
globals. Astroid is unable to handle this type of code.

Without these hooks, the following are erroneously triggered by Pylint:
    * E1101: Module 'signal' has no 'Signals' member (no-member)
    * E1101: Module 'signal' has no 'Handlers' member (no-member)
    * E1101: Module 'signal' has no 'Sigmasks' member (no-member)
"""


from astroid.brain.helpers import register_module_extender
from astroid.builder import parse
from astroid.manager import AstroidManager


def _signals_enums_transform():
    """Generates the AST for 'Signals', 'Handlers' and 'Sigmasks' IntEnums."""    
    return parse(
        _signals_enum() + _handlers_enum() + _sigmasks_enum()
    )


def _signals_enum():
    """Generates the source code for the Signals int enum."""
    return """
    class Signals(enum.IntEnum):
        SIGABRT = enum.auto()
        SIGEMT  = enum.auto()
        SIGFPE  = enum.auto()
        SIGILL  = enum.auto()
        SIGINFO = enum.auto()
        SIGINT  = enum.auto()
        SIGSEGV = enum.auto()
        SIGTERM = enum.auto()
        if sys.platform != "win32":
            SIGALRM   = enum.auto()
            SIGBUS    = enum.auto()
            SIGCHLD   = enum.auto()
            SIGCONT   = enum.auto()
            SIGHUP    = enum.auto()
            SIGIO     = enum.auto()
            SIGIOT    = enum.auto()
            SIGKILL   = enum.auto()
            SIGPIPE   = enum.auto()
            SIGPROF   = enum.auto()
            SIGQUIT   = enum.auto()
            SIGSTOP   = enum.auto()
            SIGSYS    = enum.auto()
            SIGTRAP   = enum.auto()
            SIGTSTP   = enum.auto()
            SIGTTIN   = enum.auto()
            SIGTTOU   = enum.auto()
            SIGURG    = enum.auto()
            SIGUSR1   = enum.auto()
            SIGUSR2   = enum.auto()
            SIGVTALRM = enum.auto()
            SIGWINCH  = enum.auto()
            SIGXCPU   = enum.auto()
            SIGXFSZ   = enum.auto()
        if sys.platform == "win32":
            SIGBREAK  = enum.auto()
        if sys.platform != "darwin" and sys.platform != "win32":
            SIGCLD    = enum.auto()
            SIGPOLL   = enum.auto()
            SIGPWR    = enum.auto()
            SIGRTMAX  = enum.auto()
            SIGRTMIN  = enum.auto()
    """


def _handlers_enum():
    """Generates the source code for the Handlers int enum."""
    return """
    class Handlers(enum.IntEnum):
        SIG_DFL = enum.auto()
        SIG_IGN = eunm.auto()
    """


def _sigmasks_enum():
    """Generates the source code for the Sigmasks int enum."""
    return """
    if sys.platform != "win32":
        class Sigmasks(enum.IntEnum):
            SIG_BLOCK   = enum.auto()
            SIG_UNBLOCK = enum.auto()
            SIG_SETMASK = enum.auto()
    """


register_module_extender(AstroidManager(), "signal", _signals_enums_transform)
