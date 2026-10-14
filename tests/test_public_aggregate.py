import datetime as dt
import json
import unittest
from unittest.mock import patch

import build_public_aggregate as pub


def row(case_id, day, finished=True, hn='264188'):
    r = [''] * 56
    r[1], r[2], r[13], r[15] = case_id, f'{day}/10/2569', 'ผู้ป่วยทดสอบ', hn
    r[11] = '15:00:00' if finished else ''
    return r


class PublicAggregateTests(unittest.TestCase):
    def setUp(self):
        self.header = [''] * 56
        for i, title in pub.EXPECTED.items():
            self.header[i] = title
        self.today = dt.date(2026, 10, 14)

    def calculate(self, rows, previous=None):
        with patch.object(pub.cross, 'hn_collisions', return_value=[]), \
             patch.object(pub.cross, 'an_duplicates', return_value=[]), \
             patch.object(pub.cross, 'room_overlaps', return_value=[]), \
             patch.object(pub.site, 'missing_cols', side_effect=lambda r: ['Risk'] if r[1] == 'NEWCASE1' else []):
            return pub.compute([self.header] + rows, self.today, previous)

    def test_cutoff_unfinished_and_resolved_observation(self):
        previous = {'all_cases': [{'hn': '264188', 'date': '12/10/2569', 'month_key': '2569-10'}]}
        public, state, _ = self.calculate([row('OLDCASE1', 12), row('NEWCASE1', 13, hn='88888'),
                                          row('UNFINISH', 11, False, '77777'),
                                          row('TODAYNOW', 14, hn='66666')], previous)
        self.assertEqual((public['finished'], public['pending'], public['unfinished'], public['resolved_observed']),
                         (2, 1, 1, 1))
        self.assertEqual(public['types'], [{'label': 'Risk', 'count': 1}])
        self.assertNotIn('TODAYNOW', state['observed'])
        for content in (json.dumps(public, ensure_ascii=False), pub.render(public, 'index'), pub.render(public, 'dashboard')):
            for token in ('264188', 'OLDCASE1', 'ผู้ป่วยทดสอบ', '88888', 'NEWCASE1'):
                self.assertNotIn(token, content)

    def test_empty_first_day_and_shifted_header_fail_closed(self):
        public, _, _ = pub.compute([self.header], dt.date(2026, 11, 1))
        self.assertEqual((public['finished'], public['pending'], public['resolved_observed']), (0, 0, 0))
        bad_header = self.header[:]
        bad_header[15] = 'Department'
        with self.assertRaises(ValueError):
            pub.compute([bad_header], self.today)

    def test_deleted_or_unfinished_tracked_not_resolved(self):
        state = {'seeded': True, 'observed': {'LOSTCASE': '2569-10', 'UNFINISH': '2569-10'}}
        public, _, _ = pub.compute([self.header, row('UNFINISH', 10, False)], self.today, state=state)
        self.assertEqual(public['resolved_observed'], 0)


if __name__ == '__main__':
    unittest.main()
