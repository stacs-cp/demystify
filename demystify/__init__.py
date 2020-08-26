import multiprocessing
 
multiprocessing.set_start_method('fork')
assert multiprocessing.get_start_method() == 'fork'