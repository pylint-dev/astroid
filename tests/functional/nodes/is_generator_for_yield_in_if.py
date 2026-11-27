import asyncio

def paused_iter(iterable):  # is_generator(): True
    if (yield from asyncio.sleep(0.01)):
        pass
        return
