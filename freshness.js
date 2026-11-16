// Every visit resolves a fresh release manifest before fetching its exact dataset.
export async function fetchUpdateManifest(fetcher=fetch, now=Date.now) {
  const response=await fetcher(`update.json?t=${now()}`,{cache:'no-store',credentials:'omit'});
  if(!response.ok)throw Error(`无法检查数据更新 (${response.status})`);
  const update=await response.json();
  if(!/^\d{14}$/.test(String(update.sourceVersion))||!/^\w{64}$/.test(update.dataSha256)||!Number.isFinite(Date.parse(update.checkedAt)))throw Error('更新清单格式无效');
  return update;
}
export const revisionChanged=(before,after)=>before.sourceVersion!==after.sourceVersion||before.dataSha256!==after.dataSha256||before.matchIndexSha256!==after.matchIndexSha256;
export async function loadLatestSnapshot(fetcher=fetch,now=Date.now) {
  let failure;
  for(let attempt=0;attempt<3;attempt++) {
    try {
      const update=await fetchUpdateManifest(fetcher,now);
      const query=new URLSearchParams({v:update.sourceVersion,release:update.checkedAt,t:String(now()),attempt:String(attempt)});
      const response=await fetcher(`data.json?${query}`,{cache:'no-store',credentials:'omit'});
      if(!response.ok)throw Error(`无法载入数据 (${response.status})`);
      const bytes=await response.arrayBuffer();
      const digest=await crypto.subtle.digest('SHA-256',bytes);
      const hash=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
      if(hash!==update.dataSha256)throw Error('数据发布正在切换，请稍后刷新');
      const data=JSON.parse(new TextDecoder().decode(bytes));
      if(String(data.meta.version)!==String(update.sourceVersion))throw Error('数据版本不一致');
      return {data,update};
    } catch(error) { failure=error; }
  }
  throw failure;
}
