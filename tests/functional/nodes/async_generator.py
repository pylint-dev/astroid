async def a_iter(n):
    for i in range(1, n + 1):
        yield i
        await asyncio.sleep(1)
# +4: inferred: AsyncGenerator(builtins.async_generator)
# +3: inferred.display_type(): 'AsyncGenerator'
# +2: inferred.getattr(__aiter__): BoundMethod(builtins.async_generator.__aiter__)
# +1: inferred.getattr(__anext__): BoundMethod(builtins.async_generator.__anext__)
a_iter(2)
