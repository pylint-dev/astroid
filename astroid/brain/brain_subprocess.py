# Copyright (c) 2016 Claudiu Popa <pcmanticore@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

import sys

import six

import astroid


PY33 = sys.version_info >= (3, 3)


def _subprocess_transform():
    if six.PY3:
        communicate = (bytes('string', 'ascii'), bytes('string', 'ascii'))
        communicate_signature = 'def communicate(self, input=None, timeout=None)'
        init = """
        def __init__(self, args, bufsize=0, executable=None,
                     stdin=None, stdout=None, stderr=None,
                     preexec_fn=None, close_fds=False, shell=False,
                     cwd=None, env=None, universal_newlines=False,
                     startupinfo=None, creationflags=0, restore_signals=True,
                     start_new_session=False, pass_fds=()):
            pass
        """
    else:
        communicate = ('string', 'string')
        communicate_signature = 'def communicate(self, input=None)'
        init = """
        def __init__(self, args, bufsize=0, executable=None,
                     stdin=None, stdout=None, stderr=None,
                     preexec_fn=None, close_fds=False, shell=False,
                     cwd=None, env=None, universal_newlines=False,
                     startupinfo=None, creationflags=0):
            pass
        """
    if PY33:
        wait_signature = 'def wait(self, timeout=None)'
    else:
        wait_signature = 'def wait(self)'
    if six.PY3:
        ctx_manager = '''
        def __enter__(self): return self
        def __exit__(self, *args): pass
        '''
    else:
        ctx_manager = ''
    code = '''
    class Popen(object):
        returncode = pid = 0
        stdin = stdout = stderr = file()

        %(init)s

        %(communicate_signature)s:
            return %(communicate)r
        %(wait_signature)s:
            return self.returncode
        def poll(self):
            return self.returncode
        def send_signal(self, signal):
            pass
        def terminate(self):
            pass
        def kill(self):
            pass
        %(ctx_manager)s
       ''' % {'init': init,
              'communicate': communicate,
              'communicate_signature': communicate_signature,
              'wait_signature': wait_signature,
              'ctx_manager': ctx_manager}
    return astroid.parse(code)


astroid.register_module_extender(astroid.MANAGER, 'subprocess', _subprocess_transform)
