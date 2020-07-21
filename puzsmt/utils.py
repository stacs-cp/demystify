import math
import itertools

from typing import List
# Some boring utility functions

# Flatten a (possibly even more nested) list of lists
def flatten_internal(arr):
  for i in arr:
    if isinstance(i, list):
      yield from flatten(i)
    else:
      yield i

def flatten(arr:List) -> List:
  return list(flatten_internal(arr))

def intsqrt(i: int) -> int:
  root = int(math.sqrt(i) + 0.5)
  assert root*root == i
  return root

def chainlist(*lists):
  return list(itertools.chain(*lists))