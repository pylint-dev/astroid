# +4: getattr(g)[0].args.type_comment_args: [Attribute(np.array)]
# +3: getattr(g)[0].args.type_comment_args[0]: Attribute(np.array)
# +2: getattr(g)[0].args.type_comment_args[0].parent: Expr(np.array)
# +1: getattr(g)[0].args.type_comment_args[0].parent.parent: Arguments(x)
class D:
    @staticmethod
    def g(
            x  # type: np.array
    ):
        pass
