import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const output=fs.existsSync(new URL('../dist/index.html',import.meta.url))?'../dist/':'../';
const {metrics,percentile,rankPlayers,playerGames,championStats}=await import(new URL(output+'model.js',import.meta.url));
const data=JSON.parse(fs.readFileSync(new URL(output+'data.json',import.meta.url)));

test('snapshot covers every Worlds series and individual game, including the final',()=>{
  assert.equal(Object.keys(data.matches).length,data.meta.series);
  assert.equal(Object.values(data.matches).reduce((s,m)=>s+m.games.length,0),data.meta.games);
  const f=data.matches['worlds-2026-main-event-finals-1'];
  assert.equal(f.a.n,'Bilibili Gaming');assert.equal(f.b.n,'Gen.G');
  assert.equal(f.sa,3);assert.equal(f.sb,1);assert.equal(f.games.length,4);
  assert.equal(data.meta.eventEnd,'2026-11-14');
});
test('historical directory spans the earliest available seasons and includes retired players',()=>{
  assert.ok(data.archive.players.length>12000);
  assert.ok(data.archive.events.some(e=>e[2]==='2011'));
  assert.ok(data.archive.events.some(e=>e[2]==='2026'));
  assert.ok(data.archive.players.some(p=>p[0]==='Uzi'));
  assert.ok(data.profiles.faker.years.some(y=>y.y==='2013'));
});
test('KDA and time-weighted rates derive from raw totals',()=>{
  const raw=data.stages.all.players.find(p=>p.u==='knight'),p=metrics(raw);
  assert.equal(p.kda,(raw.k+raw.a)/Math.max(1,raw.d));assert.equal(p.dpm,raw.dmg/raw.dm);
  assert.equal(p.gd15,raw.g15/raw.tn);assert.equal(p.kp,(raw.k+raw.a)/raw.tk);
});
test('side mapping remains correct when blue/red sides change across final games',()=>{
  const k=playerGames(data,'knight').filter(g=>g.id==='worlds-2026-main-event-finals-1');
  assert.equal(k.length,4);assert.equal(k.filter(g=>g.win).length,3);
  assert.ok(k.every(g=>g.team.n==='Bilibili Gaming'&&g.opp.n==='Gen.G'));
  const c=playerGames(data,'chovy').filter(g=>g.id==='worlds-2026-main-event-finals-1');
  assert.equal(c.filter(g=>g.win).length,1);
});
test('champion aggregation reconciles with event totals',()=>{
  const games=playerGames(data,'knight'),stats=championStats(games);
  assert.equal(games.length,19);assert.equal(stats.reduce((s,c)=>s+c.g,0),19);
  assert.equal(stats.reduce((s,c)=>s+c.w,0),14);
  assert.equal(stats.reduce((s,c)=>s+c.k,0),data.stages.all.players.find(p=>p.u==='knight').k);
});
test('ties receive midpoint ranks and death rate is reversed',()=>{
  assert.equal(percentile(2,[1,2,2,3]),50);
  assert.equal(percentile(1,[1,2,3,4],false),87.5);
  assert.equal(percentile(null,[1,2,3]),null);
});
test('missing denominators stay unknown and cannot produce a fabricated radar score',()=>{
  const p=metrics({k:1,a:2,d:0,g:1,w:1,min:0,dm:0,vmin:0,tn:0,tk:0});
  for(const key of ['dpm','vpm','gd15','kp','csm'])assert.equal(p[key],null);
  assert.equal(rankPlayers([{u:'missing',r:'Mid',g:3,k:1,a:2,d:0,min:0}])[0].score,null);
});
test('radar normalizes only against the same role',()=>{
  const rows=rankPlayers(data.stages.all.players);
  for(const p of rows){assert.equal(p.peers,rows.filter(q=>q.r===p.r&&q.g>=3).length);for(const v of p.radar)assert.ok(v===null||(v>=0&&v<=100));}
});
