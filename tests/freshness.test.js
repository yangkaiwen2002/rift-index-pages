import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
const output=fs.existsSync(new URL('../dist/index.html',import.meta.url))?'../dist/':'../';
const {loadLatestSnapshot,revisionChanged}=await import(new URL(output+'freshness.js',import.meta.url));
const data=JSON.stringify({meta:{version:'20261116131550'}});
const update={sourceVersion:'20261116131550',checkedAt:'2026-11-16T13:00:00Z',dataSha256:createHash('sha256').update(data).digest('hex')};
test('a visit bypasses stale caches and loads the exact release',async()=>{
  const calls=[];
  const result=await loadLatestSnapshot(async(url,options)=>{calls.push([url,options]);return new Response(url.startsWith('update.json')?JSON.stringify(update):data);},()=>123456);
  assert.equal(result.data.meta.version,update.sourceVersion);
  assert.equal(calls.length,2);
  assert.match(calls[0][0],/t=123456/);
  assert.match(calls[1][0],/v=20261116131550/);
  assert.ok(calls.every(([,options])=>options.cache==='no-store'&&options.credentials==='omit'));
});
test('a mixed CDN release is retried until the manifest and data agree',async()=>{
  let reads=0;
  const result=await loadLatestSnapshot(async url=>new Response(url.startsWith('update.json')?JSON.stringify(update):(++reads===1?'{}':data)));
  assert.equal(reads,2);assert.equal(result.update.dataSha256,update.dataSha256);
});
test('persistent corruption fails visibly instead of returning stale or incomplete data',async()=>{
  let reads=0;
  await assert.rejects(loadLatestSnapshot(async url=>{reads++;return new Response(url.startsWith('update.json')?JSON.stringify(update):'{}');}),/数据发布正在切换/);
  assert.equal(reads,6);
});
test('same source version with corrected payload still counts as an update',()=>{
  assert.equal(revisionChanged(update,{...update,dataSha256:'new-digest'}),true);
  assert.equal(revisionChanged(update,{...update,checkedAt:'2026-11-17T00:00:00Z'}),false);
});
