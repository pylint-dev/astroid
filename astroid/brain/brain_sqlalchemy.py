import astroid


def _session_transform():
    return astroid.parse(
        """
    from sqlalchemy.orm.session import Session

    class sessionmaker:
        def __init__(
            self,
            bind=None,
            class_=Session,
            autoflush=True,
            autocommit=False,
            expire_on_commit=True,
            info=None,
            **kw
        ):
            return

        def __call__(self, **local_kw):
            return Session()

        def configure(self, **new_kw):
            return

        return Session()
    """
    )


astroid.register_module_extender(
    astroid.MANAGER, "sqlalchemy.orm.session", _session_transform
)
