async def func():  # col_offset: 0  # lineno: 1
    async for i in range(10):  # col_offset: 4  # lineno: 2
        f = __(await i)  # col_offset: 15  # lineno: 3  # value: Name(i)
    async with test():  # col_offset: 4  # lineno: 4
        pass
    async for i                     in range(10):  # col_offset: 4  # lineno: 6
        pass
    async with test(),                     test2():  # col_offset: 4  # lineno: 8
        pass
