``t``-strings (:class:`TemplateStr`) are now inferred: a t-string is inferred as
an instance of ``string.templatelib.Template`` and an interpolation field as an
instance of ``string.templatelib.Interpolation``. Their members are
reconstructed from the actual template contents, so ``Template.strings`` /
``values`` / ``interpolations`` and ``Interpolation.value`` / ``expression`` /
``conversion`` / ``format_spec`` infer to the same values as at runtime. The
standard library defines those classes via ``type(t"...")``, which is not
statically inferable, so a brain plugin rebuilds the real classes from the live
objects. ``as_string`` now also doubles literal braces in the constant parts of
a t-string so the rendered code round-trips.

Closes #2789
