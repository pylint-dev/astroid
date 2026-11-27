# Test correct handling of applying binary operator to self.
import sys
sys.path = ['foo'] + sys.path
sys.path.insert(0, 'bar')
path = sys.path  # inferred-type: List | List | Uninferable
