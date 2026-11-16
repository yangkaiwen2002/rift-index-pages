import copy,datetime,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import sync_matches as sync
UTC=datetime.timezone.utc
class MatchSyncTests(unittest.TestCase):
    def feed(self,state='unstarted'):
        return {'at':datetime.datetime.now(UTC).isoformat(),'events':[{'type':'match','startTime':'2027-01-05T10:00:00Z','state':state,'league':{'slug':'lck','name':'LCK'},'match':{'id':'123','strategy':{'count':3},'teams':[{'name':'T1','code':'T1','result':{'gameWins':0}},{'name':'Gen.G','code':'GEN','result':{'gameWins':0}}]}}]}
    def test_future_schedule_has_no_fabricated_zero_zero_result(self):
        row=sync.schedule_rows(self.feed(),2026)[0]
        self.assertEqual(row['year'],'2027');self.assertIsNone(row['sa']);self.assertIsNone(row['sb'])
    def test_timezone_rollover_and_missing_precision(self):
        self.assertEqual(sync.date_info('2026-12-31 20:00','2026')[2],'2027')
        self.assertEqual(sync.date_info('2026-11-16','2026')[1],'day')
        self.assertEqual(sync.date_info(None,'2026'),(None,'unknown','2026'))
    def test_legacy_league_aliases_and_regional_finals(self):
        self.assertEqual(sync.family('EU LCS 2014','Europe League Championship Series'),'LEC')
        self.assertEqual(sync.family('Champions 2012','LoL The Champions'),'LCK')
        self.assertEqual(sync.family('LPL 2026 Regional Finals',''),'LPL')
        self.assertIsNone(sync.family('LCK AS 2025','LCK Academy Series'))
    def test_schedule_refreshes_even_without_a_new_stats_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data.json').write_text(json.dumps({'meta':{'version':'20261116131550'}}))
            (root/'match-index.json').write_text(json.dumps({'formatVersion':1,'sourceVersion':'20261116131550','archiveCount':28843,'years':{},'events':[],'leagues':['LCK']}))
            with patch.object(sync,'OUT',root),patch.object(sync,'CACHE',root/'.cache'),patch.object(sync,'get',return_value=self.feed()) as get,patch.object(sync,'write_update_status') as write:
                sync.main();get.assert_called_once_with(sync.SCHEDULE_URL);write.assert_called_once()
            self.assertEqual(json.loads((root/'matches/schedule.json').read_text())['matches'][0]['id'],'riot-123')
    def test_stale_schedule_does_not_replace_the_previous_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data.json').write_text(json.dumps({'meta':{'version':'20261116131550'}}))
            old=json.dumps({'sourceVersion':'20261116131550'});(root/'match-index.json').write_text(old)
            stale=self.feed();stale['stale']=True
            with patch.object(sync,'OUT',root),patch.object(sync,'get',return_value=stale):
                with self.assertRaises(ValueError):sync.main()
            self.assertEqual((root/'match-index.json').read_text(),old)
if __name__=='__main__':unittest.main()
