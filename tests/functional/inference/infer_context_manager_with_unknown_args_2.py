class client_log(object):
    def __init__(self, client=24):
        self.client = client
    def __enter__(self):
        return self.client
    def __exit__(self, exc_type, exc_value, traceback):
        pass

with client_log(None) as c:
    c  # inferred: Const(24) | Uninferable
