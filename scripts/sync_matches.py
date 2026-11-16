#!/usr/bin/env python3
"""Daily multi-league results and Riot's published schedule, via RiftWise public JSON."""
import argparse,collections,concurrent.futures,datetime,hashlib,json,re,unicodedata
from pathlib import Path
from sync_data import OUT,CACHE,get,atomic_json,write_update_status

LEAGUES={
 'Tencent LoL Pro League':'LPL','LoL Pro League':'LPL',
 'LoL Champions Korea':'LCK','LoL The Champions':'LCK',
 'LoL EMEA Championship':'LEC','Europe League Championship Series':'LEC',
 'Mid-Season Invitational':'MSI','World Championship':'Worlds','First Stand':'First Stand',
 'League of Legends Championship Series':'LCS','North America League Championship Series':'LCS',
 'League of Legends Championship of The Americas':'LTA',
 'League of Legends Championship of The Americas North':'LTA',
 'League of Legends Championship of The Americas South':'LTA',
 'League of Legends Championship Pacific':'LCP','Pacific Championship Series':'PCS',
 'Circuit Brazilian League of Legends':'CBLOL','Vietnam Championship Series':'VCS',
 'LoL Japan League':'LJL','Latin America League':'LLA','LCK Challengers League':'LCK CL',
 'LoL Development League':'LDL','European Masters':'EMEA Masters','EMEA Masters':'EMEA Masters',
}
RIOT_LEAGUES={'worlds':'Worlds','msi':'MSI','first_stand':'First Stand','lck':'LCK','lpl':'LPL','lec':'LEC','lcs':'LCS','lta':'LTA','lta_n':'LTA','lta_s':'LTA','lcp':'LCP','lcp_promotion':'LCP','cblol-brazil':'CBLOL','vcs':'VCS','ljl':'LJL','lla':'LLA','emea_masters':'EMEA Masters','demacia_cup':'Demacia Cup'}
FORMAT_VERSION=1
SCHEDULE_URL='https://riftwise.gg/api/push/schedule'
UTC=datetime.timezone.utc
HK=datetime.timezone(datetime.timedelta(hours=8))

def slugify(text):
    for old,new in [('ø','o'),('Ø','o'),('æ','ae'),('Æ','ae'),('ß','ss')]:text=text.replace(old,new)
    text=unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',re.sub(r"['’`.]",'',text.replace('&',' and '))).strip('-')[:70].rstrip('-')

def family(name,league):
    if league in LEAGUES:return LEAGUES[league]
    if league:return None  # Never classify academy leagues as their top league by name prefix.
    for prefix,label in [('LCK CL ','LCK CL'),('LCK ','LCK'),('LPL ','LPL'),('LEC ','LEC'),('EU LCS ','LEC'),('NA LCS ','LCS'),('LCS ','LCS'),('LTA ','LTA'),('LCP ','LCP'),('MSI ','MSI'),('Worlds ','Worlds'),('First Stand ','First Stand')]:
        if name.startswith(prefix):return label
    return None

def date_info(value,fallback_year):
    raw=(value or '').strip()
    if not raw:return None,'unknown',str(fallback_year)
    precision='day' if len(raw)==10 else 'minute'
    try:
        date=datetime.datetime.fromisoformat(raw.replace('Z','+00:00'))
        if date.tzinfo is None:date=date.replace(tzinfo=UTC)
        return date.isoformat().replace('+00:00','Z'),precision,str(date.astimezone(HK).year)
    except ValueError:return None,'unknown',str(fallback_year)

def archive_rows(event,league):
    rows=[]
    for stage in event.get('stages',[]):
        for position,item in enumerate(stage.get('series',[])):
            date,precision,year=date_info(item.get('date'),event.get('year',''))
            a,b=item.get('sa'),item.get('sb');bo=item.get('bo') or 1
            completed=item.get('w') in (1,2) or (a is not None and b is not None and a+b>=bo)
            rows.append({'id':item.get('g') or f"{event['u']}-{slugify(stage.get('name',''))}-{position}",
              'slug':item.get('g'),'event':event['u'],'eventName':event['n'],'league':league,'year':year,
              'stage':stage.get('name',''),'date':date,'precision':precision,'bo':bo,
              'a':{'n':item.get('a') or 'TBD','u':item.get('au'),'c':item.get('ac')},
              'b':{'n':item.get('b') or 'TBD','u':item.get('bu'),'c':item.get('bc')},
              'sa':a if completed else None,'sb':b if completed else None,
              'status':'completed' if completed else 'unstarted','source':'archive','parents':[]})
    return rows

def schedule_rows(payload,year):
    if not isinstance(payload.get('events'),list) or not payload.get('at'):
        raise ValueError('Invalid schedule response')
    rows=[]
    for event in payload['events']:
        if event.get('type')!='match':continue
        match=event.get('match',{});teams=match.get('teams',[])
        if len(teams)!=2 or not match.get('id'):raise ValueError('Incomplete schedule match')
        league=event.get('league',{});name=RIOT_LEAGUES.get(league.get('slug'),league.get('name') or '其他赛事')
        date,precision,y=date_info(event.get('startTime'),year)
        state=match.get('state') or event.get('state') or 'unstarted'
        state={'completed':'completed','inProgress':'inProgress','unstarted':'unstarted','canceled':'canceled','cancelled':'canceled'}.get(state,'unknown')
        def team(raw):return {'n':raw.get('name','TBD').strip(),'u':None,'c':raw.get('code'),'image':(raw.get('image') or '').replace('http:','https:')}
        score=lambda t:t.get('result',{}).get('gameWins') if state in ['completed','inProgress'] else None
        rows.append({'id':'riot-'+str(match['id']),'slug':None,'event':'riot-'+str(league.get('slug','unknown'))+'-'+y,
          'eventName':name+' '+y+' · 官方赛程','league':name,'leagueSlug':league.get('slug'),'year':y,
          'stage':event.get('blockName',''),'date':date,'precision':precision,'bo':match.get('strategy',{}).get('count'),
          'a':team(teams[0]),'b':team(teams[1]),'sa':score(teams[0]),'sb':score(teams[1]),
          'status':state,'source':'riot','parents':[]})
    return list({r['id']:r for r in rows}.values())

def file_record(path):
    return {'file':str(path.relative_to(OUT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def main(force=False):
    data=json.loads((OUT/'data.json').read_text());version=data['meta']['version']
    prior=json.loads((OUT/'match-index.json').read_text()) if (OUT/'match-index.json').exists() else None
    current_year=datetime.datetime.now(HK).year
    # Always refresh the independent schedule, even when the statistics snapshot has not changed.
    feed=get(SCHEDULE_URL)
    feed_at=datetime.datetime.fromisoformat(feed['at'].replace('Z','+00:00'))
    if feed.get('stale') or datetime.datetime.now(UTC)-feed_at>datetime.timedelta(hours=48):
        raise ValueError('Schedule provider returned a stale feed; preserving last published release')
    upcoming=schedule_rows(feed,current_year)
    CACHE.mkdir(exist_ok=True);(OUT/'matches').mkdir(exist_ok=True)
    index=dict(prior or {})
    if force or not prior or prior.get('sourceVersion')!=version or prior.get('formatVersion')!=FORMAT_VERSION:
        candidates=[]
        for row in data['archive']['events']:
            league=family(row[0],row[3])
            if league and int(row[2])<=current_year+1:
                candidates.append((row[1] or slugify(row[0]),league))
        print('Fetching match archives:',len(candidates),'events',flush=True)
        def fetch(item):
            slug,league=item;cache=CACHE/(version+'-event-'+slug+'.json')
            if cache.exists():event=json.loads(cache.read_text())
            else:event=get(data['meta']['sourceSnapshot']+'/hub/event/'+slug+'.json');atomic_json(cache,event)
            if not event.get('u') or not event.get('n'):raise ValueError('Invalid event: '+slug)
            return event,league
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:events=list(pool.map(fetch,candidates))
        parents=collections.defaultdict(set)
        for event,_ in events:
            for child in event.get('children',[]):parents[child['u']].add(event['u'])
            if event.get('parent'):parents[event['u']].add(event['parent']['u'])
        def ancestors(slug,seen=None):
            seen=set(seen or []);direct=parents[slug]-seen;seen.update(direct)
            for p in direct:seen.update(ancestors(p,seen))
            return seen
        unique={};catalog={}
        for event,league in events:
            catalog[event['u']]={'u':event['u'],'n':event['n'],'league':league,'years':[]}
            for row in archive_rows(event,league):
                row['parents']=sorted(ancestors(event['u']))
                if row['id'] in unique:
                    old=unique[row['id']];old['parents']=sorted(set(old['parents']+row['parents']+[row['event']])-set([old['event']]))
                else:unique[row['id']]=row
        groups=collections.defaultdict(list)
        for row in unique.values():
            groups[row['year']].append(row)
            for slug in [row['event']]+row['parents']:
                if slug in catalog and row['year'] not in catalog[slug]['years']:catalog[slug]['years'].append(row['year'])
        if len(unique)<10000:raise ValueError('Unexpectedly incomplete historical match archive')
        for required in ['LPL','LCK','LEC','MSI','Worlds']:
            if not any(r['league']==required for r in unique.values()):raise ValueError('Missing league: '+required)
        if prior and prior.get('formatVersion')==FORMAT_VERSION and len(unique)<prior.get('archiveCount',0)*.95:raise ValueError('Historical match archive unexpectedly shrank')
        years={}
        for y,rows in sorted(groups.items()):
            rows.sort(key=lambda r:(r['date'] or '',r['id']),reverse=True)
            path=OUT/'matches'/f'{y}.json';atomic_json(path,rows)
            years[y]={**file_record(path),'count':len(rows),'leagues':sorted(set(r['league'] for r in rows))}
        index={'formatVersion':FORMAT_VERSION,'sourceVersion':version,'sourceBuiltAt':data['meta']['built'],'archiveCount':len(unique),
          'years':years,'events':[e for e in catalog.values() if e['years']],
          'leagues':sorted(set(r['league'] for r in unique.values()))}
        print('Historical series:',len(unique),'years:',list(years),flush=True)
    # Keep recent official results and all published upcoming matches separate from immutable archive shards.
    schedule={'source':'Riot LoL Esports via RiftWise','sourceUrl':SCHEDULE_URL,'asOf':feed['at'],
      'checkedAt':datetime.datetime.now(UTC).isoformat(),'matches':upcoming}
    atomic_json(OUT/'matches'/'schedule.json',schedule)
    index['schedule']=file_record(OUT/'matches'/'schedule.json')
    index['checkedAt']=schedule['checkedAt'];index['scheduleAsOf']=feed['at']
    atomic_json(OUT/'match-index.json',index)
    write_update_status(data)
    print('Schedule:',len(upcoming),'matches, updated',feed['at'],flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--force',action='store_true');main(parser.parse_args().force)
