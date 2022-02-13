import models


def func():
    for _, value in models.__dict__.items():
        if isinstance(value, type):
            value.class_attribute += 1
