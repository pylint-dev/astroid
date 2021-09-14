# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
"""Astroid hooks for the signal library.

The signal module generates the 'Signals', 'Handlers' and 'Sigmasks' IntEnums
dynamically using the IntEnum._convert() classmethod, which modifies the module
globals. Pylint is unable to handle this type of code.

Without these hooks, the following are erroneously triggered:
    * E1101: Module 'signal' has no 'Signals' member (no-member)
    * E1101: Module 'signal' has no 'Handlers' member (no-member)
    * E1101: Module 'signal' has no 'Sigmasks' member (no-member)
"""


from astroid.brain.helpers import register_module_extender
from astroid.builder import parse
from astroid.manager import AstroidManager


def _signals_enum_transform():
    """Generates the AST for 'Signals', 'Handlers' and 'Sigmasks' IntEnums.

    This is done by simply importing the signal library and extracting the
    enums that are generated correctly at runtime.

    The existance of 'Sigmasks' is checked first, as it is only generated by
    the signal library if 'pthread_sigmask()' is supported by the OS.
    """
    return parse(
        """
        import signal
        Signals = signal.Signals
        Handlers = signal.Handlers
        if hasattr(signal, "Sigmasks"):
            Sigmasks = signal.Sigmasks
        """
    )


register_module_extender(AstroidManager(), "signal", _signals_enum_transform)
