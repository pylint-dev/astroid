from ..plugin_api import top_message


def plugin_message(msg):
    return f"plugin_message: {top_message(msg)}"