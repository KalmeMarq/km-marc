import unittest

from kmmarc.marc import Leader, Record
from kmmarc.reader import MarcJsonReader

class TestSimple(unittest.TestCase):
    def test_leader(self):
        self.assertEqual(Leader("01028nam0 2200277   450 ").marshal(), "01028nam0 2200277   450 ")
    
    def test_record_leader(self):
        self.assertEqual(Record("01028nam0 2200277   450 ").leader.marshal(), "01028nam0 2200277   450 ")

    def test_json_reader_leader(self):
        f = open("res/testeExportacao.iso", "rb")

        reader = MarcJsonReader(f)

        self.assertEqual(list(reader)[0].leader.marshal(), "01028nam0 2200277   450 ")

        f.close()


if __name__ == '__main__':
    unittest.main()