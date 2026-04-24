import unittest

from pages.process.logic import ProcessLogic


class ProcessLogicTests(unittest.TestCase):
    def test_deadline_time_slots_follow_company_window(self):
        slots = ProcessLogic.get_deadline_time_slots()
        self.assertEqual("08:00 AM", slots[0])
        self.assertEqual("11:00 PM", slots[-1])
        self.assertNotIn("08:00 PM", slots[:4])
        self.assertNotIn("11:00 AM", slots[-4:])


if __name__ == "__main__":
    unittest.main()
