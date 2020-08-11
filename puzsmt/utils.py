import math
import itertools

from typing import Iterable, List
# Some boring utility functions

# Flatten a (possibly even more nested) list of lists
def flatten_internal(arr):
  for i in arr:
    if isinstance(i, Iterable):
      yield from flatten(i)
    else:
      yield i

def flatten(arr:List) -> List:
  return list(flatten_internal(arr))

def intsqrt(i: int) -> int:
  root = int(math.sqrt(i) + 0.5)
  if root*root != i:
    return None
  else:
    return root

def chainlist(*lists):
  return list(itertools.chain(*lists))

def shuffledcopy(r, l):
  cpy = list(l)
  r.shuffle(cpy)
  return cpy