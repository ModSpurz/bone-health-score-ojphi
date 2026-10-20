"""Synthetic-only smoke tests for cohort and repeat-matching helpers."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'analysis'))
import reproduce_analysis as a


def synthetic_record(record_id, nickname, age=52, sex='Female', weight=55, height=160):
    return {
        'id': record_id,
        'created_at': '2025-10-15T01:23:45+00:00',
        'nickname': nickname,
        'input_age': str(age),
        'input_gender': sex,
        'input_weight_kg': str(weight),
        'input_height_cm': str(height),
        'input_steroids': 'false',
        'input_parent_fracture': 'false',
        'input_menopause_before_45': 'no',
        'input_fracture_history': '{"hip":false,"spine":false,"wrist_shoulder":false,"other":false}',
    }


class TestReproducibilityHelpers(unittest.TestCase):
    def test_nickname_normalization(self):
        self.assertEqual(a.nickname_key('  DemoABC '), a.nickname_key('demoabc'))
        self.assertNotEqual(a.nickname_key('demoabc'), a.nickname_key('demoabx'))

    def test_repeat_requires_anthropometric_concordance(self):
        rows = [
            synthetic_record('001', 'Demo_A'),
            synthetic_record('002', 'demo_a ', weight=55.2, height=159.8),
            synthetic_record('003', 'DEMO_A', weight=61),
            synthetic_record('004', 'OtherNick'),
        ]
        retained, stats = a.deduplicate_probable_repeats(rows)
        self.assertEqual(len(retained), 3)
        self.assertEqual(stats['repeated_nickname_groups'], 1)
        self.assertEqual(stats['probable_repeat_clusters'], 1)
        self.assertEqual(stats['subsequent_submissions_removed'], 1)

    def test_dxa_age_boundary(self):
        row = synthetic_record('101', 'Demo_B', age=50)
        row['input_steroids'] = 'true'
        self.assertFalse(a.dxa_prompt(row))
        row['input_age'] = '51'
        self.assertTrue(a.dxa_prompt(row))

    def test_menopause_default_window(self):
        row = synthetic_record('201', 'Demo_C', age=64)
        row['input_menopause_before_45'] = 'not_applicable'
        self.assertTrue(a.menopause_default(row))
        row['input_age'] = '65'
        self.assertFalse(a.menopause_default(row))


if __name__ == '__main__':
    unittest.main()
