class UnsupportedFormatCharacter(Exception):
    def __init__(self, index):
        Exception.__init__(self, index)
        self.index = index

try:
   1/0
except UnsupportedFormatCharacter as exc:
   # +2: inferred: ExceptionInstance(infer_exception_instance_attributes.UnsupportedFormatCharacter)
   # +1: inferred.getattr(index): AssignAttr
   exc
