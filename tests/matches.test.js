import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
const root=fs.existsSync(new URL('../dist/index.html',import.meta.url))?'../dist/':'../';
const {mergeMatches,matchStatus,filterMatches}=await import(new URL(root+'match-model.js',import.meta.url));
const index=JSON.parse(fs.readFileSync(new URL(root+'match-index.json',import.meta.url)));
const now=Date.parse('2026-11-16T15:00:00Z');
const asOf='2026-11-16T14:59:00Z';
const archived={id:'final',slug:'final',league:'Worlds',event:'worlds-2026-main-event',parents:['worlds-2026'],eventName:'Worlds 2026 Main Event',year:'2026',a:{n:'Bilibili Gaming',u:'bilibili-gaming',c:'BLG'},b:{n:'Gen.G',u:'geng',c:'GEN'},date:'2026-11-14T19:00:00Z',sa:3,sb:1,status:'completed'};
const official={id:'riot-final',slug:null,league:'Worlds',event:'riot-worlds-2026',parents:[],eventName:'Worlds 2026 · 官方赛程',year:'2026',a:{n:'Gen.G Esports',c:'GEN'},b:{n:'BILIBILI GAMING',c:'BLG'},date:'2026-11-14T19:00:00Z',sa:1,sb:3,status:'completed'};
test('official/archive duplicate merges without flipping the final score or losing detail links',()=>{
 const rows=mergeMatches([archived],[official]);assert.equal(rows.length,1);assert.equal(rows[0].slug,'final');assert.equal(rows[0].sa,3);assert.equal(rows[0].sb,1);
 assert.equal(filterMatches(rows,{year:'2026',league:'Worlds',event:'worlds-2026',status:'completed'},asOf,now).length,1);
 assert.equal(filterMatches(rows,{year:'2026',event:'riot-worlds-2026'},asOf,now).length,1);
});
test('stale official unstarted status cannot erase an archived completed result',()=>{
 const rows=mergeMatches([archived],[{...official,status:'unstarted',sa:null,sb:null}]);assert.equal(rows[0].status,'completed');assert.equal(rows[0].sa,3);
});
test('a past scheduled match becomes unconfirmed, never an invented live result',()=>{
 assert.equal(matchStatus({...archived,status:'unstarted'},asOf,now),'unconfirmed');
 assert.equal(matchStatus({...archived,status:'unstarted',date:'2026-11-17T10:00:00Z'},asOf,now),'unstarted');
 assert.equal(matchStatus({...archived,status:'inProgress'},'2026-11-14T00:00:00Z',now),'unconfirmed');
});
test('filters combine year, league, event, team search and match status',()=>{
 const upcoming={...archived,id:'next',league:'LCK',event:'lck-2026',parents:[],eventName:'LCK 2026',a:{n:'T1',c:'T1'},status:'unstarted',date:'2026-11-17T10:00:00Z'};
 assert.equal(filterMatches([archived,upcoming],{year:'2026',league:'LCK',event:'lck-2026',q:'T1',status:'upcoming'},asOf,now)[0].id,'next');
 assert.equal(filterMatches([archived,upcoming],{year:'2025'},asOf,now).length,0);
});
test('every year shard matches its release digest and includes all requested leagues',()=>{
 let total=0;const leagues=new Set(),ids=new Set();
 for(const [year,file]of Object.entries(index.years)){
  const bytes=fs.readFileSync(new URL(root+file.file,import.meta.url));assert.equal(createHash('sha256').update(bytes).digest('hex'),file.sha256);
  const rows=JSON.parse(bytes);assert.equal(rows.length,file.count);total+=rows.length;
  for(const r of rows){assert.equal(r.year,year);assert.ok(!ids.has(r.id));ids.add(r.id);leagues.add(r.league);}
 }
 assert.equal(total,index.archiveCount);assert.ok(total>20000);
 for(const league of ['LPL','LCK','LEC','MSI','Worlds'])assert.ok(leagues.has(league));
 assert.ok(index.years['2011']);assert.ok(index.years['2026']);
});
test('real LCK 2025 and MSI 2026 filters return historical series',()=>{
 for(const [year,league]of [['2025','LCK'],['2026','MSI']]){
  const rows=JSON.parse(fs.readFileSync(new URL(root+index.years[year].file,import.meta.url)));
  const filtered=filterMatches(rows,{year,league,status:'completed'},asOf,now);assert.ok(filtered.length>10);assert.ok(filtered.every(r=>!r.eventName.startsWith('LCK AS ')));assert.ok(filtered.filter(r=>r.slug).length>filtered.length*.9);
 }
});
