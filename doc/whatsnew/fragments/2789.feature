``t``-strings (:class:`TemplateStr`) are now inferred: a t-string is inferred as
an instance of ``string.templatelib.Template`` and an interpolation field as an
instance of ``string.templatelib.Interpolation``. Their members are
reconstructed from the actual template contents, so ``Template.strings`` /
``values`` / ``interpolations`` and ``Interpolation.value`` / ``expression`` /
``conversion`` / ``format_spec`` infer to the same values as at runtime,
including inside a called function, and adding two t-strings infers to the
concatenated template. A ``Template`` or ``Interpolation`` built by calling the
class directly is still a plain instance with uninferable members. The
standard library defines those classes via ``type(t"...")``, which is not
statically inferable, so a brain plugin rebuilds the real classes from the live
objects. ``as_string`` now also escapes literal braces and quotes in the
constant parts of a t-string so the rendered code round-trips.

Closes #2789
