# Some boring utility functions

# Flatten a (possibly even more nested) list of lists
def flatten_internal(arr):
  for i in arr:
    if isinstance(i, list):
      yield from flatten(i)
    else:
      yield i

def flatten(arr):
  return list(flatten_internal(arr))