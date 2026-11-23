from unknown import Unknown
A = []
B = []

def test():
  xyz = [
    Unknown
  ] + A + B
  return xyz

Z = test()  # inferred: List(Unknown(Unknown.Unknown()))
