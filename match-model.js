const canon=s=>String(s||'').toLowerCase().replace(/esports|gaming|alienware/g,'').replace(/[^a-z0-9]/g,'');
function sameTeam(a,b){const codes={tlaw:'tl'};const ac=canon(a.c),bc=canon(b.c);return Boolean((a.u&&a.u===b.u)||(ac&&bc&&(codes[ac]||ac)===(codes[bc]||bc))||(canon(a.n)&&canon(a.n)===canon(b.n)));}
export function mergeMatches(archive,schedule){
  const rows=archive.map(r=>({...r})),used=new Set();
  for(const fresh of schedule){
    const candidates=rows.filter(r=>!used.has(r.id)&&r.league===fresh.league&&r.date&&fresh.date&&Math.abs(Date.parse(r.date)-Date.parse(fresh.date))<36*3600000&&((sameTeam(r.a,fresh.a)&&sameTeam(r.b,fresh.b))||(sameTeam(r.a,fresh.b)&&sameTeam(r.b,fresh.a))));
    if(candidates.length!==1){rows.push({...fresh});continue;}
    const row=candidates[0],forward=sameTeam(row.a,fresh.a);used.add(row.id);
    row.officialId=fresh.id;row.date=fresh.date;row.year=fresh.year;row.precision=fresh.precision;
    row.parents=[...new Set([...(row.parents||[]),fresh.event,...(fresh.parents||[])].filter(Boolean))];
    row.a={...row.a,image:(forward?fresh.a:fresh.b).image};row.b={...row.b,image:(forward?fresh.b:fresh.a).image};
    if(row.status!=='completed'||fresh.status==='completed'){
      row.status=fresh.status;row.sa=forward?fresh.sa:fresh.sb;row.sb=forward?fresh.sb:fresh.sa;
    }
    row.source='archive+riot';
  }
  return [...new Map(rows.map(r=>[r.id,r])).values()];
}
export function matchStatus(row,asOf,now=Date.now()){
  if(['completed','canceled'].includes(row.status))return row.status;
  if(row.status==='inProgress')return now-Date.parse(asOf)<2*3600000?'inProgress':'unconfirmed';
  if(row.status==='unknown')return 'unconfirmed';
  if(row.date){const allowance=row.precision==='day'?24*3600000:3600000;if(Date.parse(row.date)+allowance<now)return 'unconfirmed';}
  return 'unstarted';
}
export function filterMatches(rows,filters,asOf,now=Date.now()){
  const q=(filters.q||'').trim().toLowerCase();
  return rows.filter(row=>{
    const status=matchStatus(row,asOf,now);
    return (!filters.year||filters.year==='all'||row.year===filters.year)&&(!filters.league||filters.league==='all'||row.league===filters.league)&&(!filters.event||filters.event==='all'||row.event===filters.event||row.parents?.includes(filters.event))&&(!filters.status||filters.status==='all'||(filters.status==='upcoming'?['unstarted','inProgress'].includes(status):status===filters.status))&&(!q||[row.a.n,row.a.c,row.b.n,row.b.c,row.league,row.eventName,row.stage].some(s=>String(s||'').toLowerCase().includes(q)));
  }).sort((a,b)=>{
    const rank=r=>({inProgress:0,unstarted:1,completed:2,unconfirmed:3,canceled:4}[matchStatus(r,asOf,now)]??4);
    const byStatus=rank(a)-rank(b);if(byStatus)return byStatus;
    const da=a.date?Date.parse(a.date):null,db=b.date?Date.parse(b.date):null;
    if(da===null)return 1;if(db===null)return -1;
    return matchStatus(a,asOf,now)==='completed'?db-da:da-db;
  });
}
const fileCache=new Map();
export async function matchFile(file,sha){
  const key=file+sha;if(fileCache.has(key))return fileCache.get(key);
  const promise=(async()=>{
    if(!/^[a-f0-9]{64}$/.test(sha||''))throw Error('比赛数据清单未就绪，请检查更新');
    const response=await fetch(`${file}?v=${sha}`,{cache:'no-store',credentials:'omit'});
    if(!response.ok)throw Error(`比赛数据暂不可用 (${response.status})`);
    const body=await response.arrayBuffer(),digest=await crypto.subtle.digest('SHA-256',body);
    const actual=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
    if(actual!==sha)throw Error('比赛数据版本正在切换，请稍后重试');
    return JSON.parse(new TextDecoder().decode(body));
  })().catch(e=>{fileCache.delete(key);throw e;});fileCache.set(key,promise);return promise;
}
