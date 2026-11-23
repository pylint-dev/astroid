from enum import Enum
class ContentType(Enum):
    TEXT, PHOTO, VIDEO, GIF, YOUTUBE, *_ = [1, 2, 3, 4, 5, 6]
# +1: inferred: Instance(enum_starred_is_skipped.ContentType.GIF) | Instance(enum_starred_is_skipped.ContentType.PHOTO) | Instance(enum_starred_is_skipped.ContentType.TEXT) | Instance(enum_starred_is_skipped.ContentType.VIDEO) | Instance(enum_starred_is_skipped.ContentType.YOUTUBE)
ContentType.TEXT
