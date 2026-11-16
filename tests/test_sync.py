import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sync_data',ROOT/'scripts/sync_data.py')
sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
OUT=ROOT/'dist' if (ROOT/'dist'/'index.html').exists() else ROOT
DATA=json.loads((OUT/'data.json').read_text())
class SnapshotSafetyTests(unittest.TestCase):
    def test_complete_existing_snapshot_is_accepted(self):sync.validate_snapshot(DATA,DATA)
    def test_partial_player_index_is_rejected(self):
        broken=copy.deepcopy(DATA);broken['archive']['players']=broken['archive']['players'][:100]
        with self.assertRaises(ValueError):sync.validate_snapshot(broken,DATA)
    def test_missing_final_game_is_rejected(self):
        broken=copy.deepcopy(DATA);broken['matches']['worlds-2026-main-event-finals-1']['games'].pop()
        with self.assertRaises(ValueError):sync.validate_snapshot(broken,DATA)
    def test_regressed_source_cannot_replace_published_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);original=json.dumps(DATA);(root/'data.json').write_text(original)
            with patch.object(sync,'OUT',root),patch.object(sync,'CACHE',root/'.cache'),patch.object(sync,'get',return_value={'version':'20200101000000','built':'2020-01-01T00:00:00Z'}):
                with self.assertRaises(ValueError):sync.main()
            self.assertEqual((root/'data.json').read_text(),original)
            self.assertFalse((root/'update.json').exists())
    def test_unchanged_upstream_refreshes_check_time_without_downloading_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);original=json.dumps(DATA);(root/'data.json').write_text(original)
            with patch.object(sync,'OUT',root),patch.object(sync,'CACHE',root/'.cache'),patch.object(sync,'get',return_value={'version':DATA['meta']['version'],'built':DATA['meta']['built']}) as get:
                sync.main()
            self.assertEqual(get.call_count,1)
            self.assertEqual((root/'data.json').read_text(),original)
            status=json.loads((root/'update.json').read_text())
            self.assertEqual(status['sourceVersion'],DATA['meta']['version'])
            self.assertEqual(len(status['dataSha256']),64)
if __name__=='__main__':unittest.main()
