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
