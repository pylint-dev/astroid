try:
    raise UnicodeDecodeError("utf-8", b"blob", 0, 1, "reason")
except UnicodeDecodeError as error:
    error.object  # inferred: Const(b'')
