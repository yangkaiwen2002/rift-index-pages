export const DIMENSIONS = [
  {key:'gd15',name:'对线',english:'LANING',unit:'经济差 @15',higher:true},
  {key:'dpm',name:'输出',english:'DAMAGE',unit:'分均伤害',higher:true},
  {key:'csm',name:'发育',english:'FARMING',unit:'分均补刀',higher:true},
  {key:'kp',name:'参团',english:'TEAMPLAY',unit:'击杀参与率',higher:true},
  {key:'vpm',name:'视野',english:'VISION',unit:'分均视野得分',higher:true},
  {key:'dpmDeath',name:'生存',english:'SURVIVAL',unit:'每分钟死亡（越低越好）',higher:false},
];
export const divide=(a,b)=>Number.isFinite(a)&&Number.isFinite(b)&&b>0?a/b:null;
export function metrics(p){
  return {...p,kda:(p.k+p.a)/Math.max(1,p.d),winrate:divide(p.w,p.g),dpm:divide(p.dmg,p.dm),csm:divide(p.cs,p.min),gpm:divide(p.gold,p.min),kp:divide(p.k+p.a,p.tk),vpm:divide(p.vis,p.vmin),gd15:divide(p.g15,p.tn),cs15:divide(p.c15,p.tn),xp15:divide(p.x15,p.tn),damageShare:divide(p.sd,p.td),goldShare:divide(p.sg,p.tg),dpmDeath:divide(p.d,p.min)};
}
export function percentile(value,values,higher=true){
  if(value==null||!Number.isFinite(value)||!values.length)return null;
  const lower=values.filter(x=>x<value).length;
  const equal=values.filter(x=>x===value).length;
  const p=(lower+equal/2)/values.length*100;
  return higher?p:100-p;
}
export function rankPlayers(rows){
  const players=rows.map(metrics);
  return players.map(p=>{
    const peers=players.filter(q=>q.r===p.r&&q.g>=3);
    const radar=DIMENSIONS.map(d=>percentile(p[d.key],peers.map(q=>q[d.key]).filter(Number.isFinite),d.higher));
    return {...p,radar,peers:peers.length,score:radar.every(Number.isFinite)?radar.reduce((a,b)=>a+b,0)/6:null};
  });
}
export function playerGames(data,slug,stage='all'){
  const games=[];
  for(const [id,m]of Object.entries(data.matches)){
    if(stage==='main'&&!m.e.includes('main-event')||stage==='playin'&&!m.e.includes('play-in'))continue;
    for(const g of m.games){
      const p=g.p.find(x=>x.u===slug);if(!p)continue;
      const teamKey=p.s===1?g.blue:(g.blue==='a'?'b':'a');
      const team=teamKey==='a'?m.a:m.b,opp=teamKey==='a'?m.b:m.a;
      games.push({...p,id,number:g.n,date:g.date||m.date,win:g.w===(teamKey==='a'?1:2),team,opp,minutes:g.min,stage:m.stage,patch:g.patch,vod:g.vgs||g.vpb,kda:(p.k+p.a)/Math.max(1,p.d)});
    }
  }
  return games.sort((a,b)=>b.date.localeCompare(a.date)||b.number-a.number);
}
export function championStats(games){
  const result={};for(const g of games){const c=result[g.c]??={c:g.c,g:0,w:0,k:0,d:0,a:0};c.g++;c.w+=Number(g.win);c.k+=g.k;c.d+=g.d;c.a+=g.a;}
  return Object.values(result).map(c=>({...c,kda:(c.k+c.a)/Math.max(1,c.d)})).sort((a,b)=>b.g-a.g||b.w-a.w);
}
