import unittest
from demystify.musdict import MusDict


class MusDictTester(unittest.TestCase):
    def test_initialisation_empty(self):
        test = MusDict()
        self.assertEqual(len(test), 0)

    def test_initialisation_dict(self):
        test = MusDict({'a': 7, 'b': 8, 'c': 9})
        self.assertEqual(len(test), 3)
        self.assertEqual(test['a'], 7)
        self.assertEqual(test['b'], 8)
        self.assertEqual(test['c'], 9)

    def classic_update(self):
        test = MusDict({'a': 7, 'b': 8, 'c': 9})
        test['testing'] = 123
        self.assertEqual(test['testing'], 123)

    def test_get(self):
        test = MusDict({'a': 7, 'b': 8, 'c': 9})
        expected = 8
        self.assertEqual(test.get('b'), expected)

    def test_contains(self):
        test = MusDict({'a': 7, 'b': 8, 'c': 9})
        self.assertTrue(test.contains('a'))
        self.assertFalse(test.contains('g'))

    def test_get_first(self):
        test = MusDict({'a': [1, 2, 3], 'b': [4, 5, 6]})
        expected_a = 1
        expected_b = 4
        self.assertEqual(test.get_first('a'), expected_a)
        self.assertEqual(test.get_first('b'), expected_b)

    def test_remove_duplicates(self):
        test = MusDict({'a': ['test1', 'dibble', 'contains x,y,z'], 'b': ['test1', 'dibble', 'contains x,y,z'], 'c':['4','5','6']})
        test.remove_duplicates()
        self.assertEqual(len(test),2)
        self.assertFalse('b' in test)

    def test_remove_duplicates_not_adjacent(self):
        test = MusDict({'a': ['test1', 'dibble', 'contains x,y,z'], 'b': ['4','5','6'], 'c': ['test1', 'dibble', 'contains x,y,z']})
        test.remove_duplicates()
        self.assertEqual(len(test),2)
        self.assertFalse('c' in test)

    def test_has_literal(self):
        #TODO change this to use literals
        test = MusDict({'grid[1,9] is 0': 7, 'grid[9,2] is 0': 8, 'grid[9,2] is not 1': 9})
        self.assertTrue(test.has_literal('grid[1,9] is 0'))
        self.assertFalse(test.has_literal('grid[9,2] is 1'))

    def test_minimum_0(self):
        test = MusDict({'grid[1,3] is 0': [()], 'grid[1,6] is 1': [()], 'grid[1,8] is 0': [()], 'grid[1,9] is 0': [('col 9 cannot have three white starting at 1!',)], 'grid[1,9] is not 1': [('col 9 cannot have three white starting at 1!',)], 'grid[2,1] is 0': [()], 'grid[2,5] is 1': [()], 'grid[2,6] is 0': [('row 2 cannot have three white starting at 5!',)], 'grid[2,6] is not 1': [('row 2 cannot have three white starting at 5!',)], 'grid[2,7] is 1': [()], 'grid[2,8] is 0': [('row 2 cannot have three white starting at 7!',)], 'grid[2,8] is not 1': [('row 2 cannot have three white starting at 7!',)], 'grid[2,9] is 1': [()], 'grid[2,10] is 0': [()]})
        self.assertEqual(test.minimum(),0)