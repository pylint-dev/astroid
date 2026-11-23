def paused_iter(iterable):  # is_generator(): True
    while True:
        # Continue to yield the same item until `next(i)` or `i.send(False)`
        while (yield value):
            pass
