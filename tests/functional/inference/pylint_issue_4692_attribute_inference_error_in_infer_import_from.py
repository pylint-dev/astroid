# Https://github.com/pylint-dev/pylint/issues/4692.
import click


for name, item in click.__dict__.items():  # inferred: InferenceError
    _ = isinstance(item, click.Command) and item != 'foo'
