import threading

import language_tool_python

_tool = None
_lock = threading.Lock()


def get_tool():
    global _tool
    if _tool is None:
        with _lock:
            if _tool is None:
                _tool = language_tool_python.LanguageTool("en-US")

    return _tool
