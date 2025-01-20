import unittest
from utils import Utils

class TestUtils(unittest.TestCase):

    def test_confirm_yes(self):
        utils = Utils()
        self.assertEqual(utils.confirm("Enter yes:"), True)

    def test_confirm_no(self):
        utils = Utils()
        self.assertEqual(utils.confirm("Enter no:"), False)

if __name__ == "__main__":
    unittest.main()
