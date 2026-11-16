#!/usr/bin/env python3
"""Snapshot public RiftWise statistics and publisher portraits. No API keys needed."""
import argparse
import os
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import re
import time
import urllib.request
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist' if (ROOT / 'dist' / 'index.html').exists() else ROOT
CACHE = ROOT / '.cache'
ORIGIN = 'https://riftwise.gg'
EXTRAS = ['uzi', 'deft', 'xiaohu', 'bdd', 'scout', 'elk', 'gala', 'aiming', 'peanut', 'rekkles', 'jankos', 'doinb', 'doublelift', 'impact', 'lehends']

def get(url, binary=False):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'RiftIndex/1.0 (public esports statistics; attributed snapshot)'})
            with urllib.request.urlopen(req, timeout=40) as response:
                body = response.read()
            return body if binary else json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == 2: raise
            time.sleep(attempt + 1)
        except Exception:
            if attempt == 2: raise
            time.sleep(attempt + 1)

def validate_snapshot(data, previous=None):
    """Reject incomplete, regressed or inconsistent snapshots before publishing."""
    meta=data['meta']
    if not re.fullmatch(r'\d{14}',str(meta['version'])):
        raise ValueError('Invalid source snapshot version')
    if previous and str(meta['version']) < str(previous['meta']['version']):
        raise ValueError('Source snapshot regressed; refusing to replace newer data')
    if len(data['matches']) != meta['series'] or meta['series'] != 46:
        raise ValueError('Worlds series coverage is incomplete')
    if sum(len(m['games']) for m in data['matches'].values()) != meta['games'] or meta['games'] != 98:
        raise ValueError('Worlds game coverage is incomplete')
    if len(data['stages']['all']['players']) != 96:
        raise ValueError('Worlds player coverage is incomplete')
    required={p['u'] for p in data['stages']['all']['players']} | set(EXTRAS)
    if not required.issubset(data['profiles']):
        raise ValueError('Required player profiles are missing')
    for name,minimum in [('players',12000),('teams',2000),('events',2000)]:
        count=len(data['archive'][name])
        if count < minimum or (previous and count < len(previous['archive'][name])*0.95):
            raise ValueError(f'Unexpectedly incomplete {name} archive: {count}')
    final=data['matches'].get('worlds-2026-main-event-finals-1',{})
    if final.get('sa') != 3 or final.get('sb') != 1:
        raise ValueError('Worlds final is missing or inconsistent')


def atomic_json(path, value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')))
    tmp.replace(path)


def write_update_status(data):
    status={
        'sourceVersion':data['meta']['version'],
        'sourceBuiltAt':data['meta']['built'],
        'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'schedule':'每天 08:17（北京时间 / 香港时间）',
        'runId':os.environ.get('GITHUB_RUN_ID'),
        'dataSha256':hashlib.sha256((OUT/'data.json').read_bytes()).hexdigest(),
    }
    if (OUT/'match-index.json').exists():
        status['matchIndexSha256']=hashlib.sha256((OUT/'match-index.json').read_bytes()).hexdigest()
    atomic_json(OUT/'update.json',status)
    print('Update status:',json.dumps(status,ensure_ascii=False),flush=True)


def main(force=False):
    previous=json.loads((OUT/'data.json').read_text()) if (OUT/'data.json').exists() else None
    CACHE.mkdir(exist_ok=True)
    (OUT / 'assets' / 'players').mkdir(parents=True, exist_ok=True)
    (OUT / 'assets' / 'teams').mkdir(parents=True, exist_ok=True)
    (OUT / 'assets' / 'champions').mkdir(parents=True, exist_ok=True)
    latest = get(ORIGIN + '/stats/latest.json?t=' + str(int(time.time())))
    version = str(latest['version'])
    if not re.fullmatch(r'\d{14}',version): raise ValueError('Invalid upstream version')
    if previous and version < str(previous['meta']['version']): raise ValueError('Upstream version regressed')
    if previous and version == str(previous['meta']['version']) and not force:
        validate_snapshot(previous,previous)
        write_update_status(previous)
        print('Already using the latest upstream snapshot; verified without re-downloading.',flush=True)
        return
    base = f'{ORIGIN}/stats/{version}'
    def snapshot(path):
        dest = CACHE / (version + '-' + path.replace('/', '_'))
        if not dest.exists():
            dest.write_text(json.dumps(get(base + '/' + path), ensure_ascii=False))
        return json.loads(dest.read_text())
    event = snapshot('hub/event/worlds-2026.json')
    assert event['end'] >= '2026-11-14', 'Snapshot does not cover the Worlds final'
    print('Snapshot:', version, 'event games:', event['games'], flush=True)
    stages = {'all': event, 'main': snapshot('hub/event/worlds-2026-main-event.json'), 'playin': snapshot('hub/event/worlds-2026-play-in.json')}
    slugs = sorted(set(p['u'] for p in event['players']) | set(EXTRAS))
    profiles, teams, matches, assets, failures = {}, {}, {}, {}, []
    def profile(slug):
        p = snapshot(f'hub/player/{slug}.json')
        keep = ['name', 'u', 'role', 'img', 'club', 'clubU', 'clubTo', 'g', 'w', 'k', 'd', 'a', 'kda', 'csm', 'gpm', 'dpm', 'teams', 'years', 'champs', 'nChamps', 'events', 'recent', 'best', 'titles']
        p = {k:p[k] for k in keep if k in p} | {'bio': {k:v for k,v in p.get('bio',{}).items() if k in ['real','native','country','cc','born']}}
        p['source'] = f'{ORIGIN}/player/{slug}'
        photo = OUT / 'assets' / 'players' / f'{slug}.webp'
        if not photo.exists() and photo.with_suffix('.png').exists(): photo = photo.with_suffix('.png')
        old_profile=previous.get('profiles',{}).get(slug,{}) if previous else {}
        if photo.exists() and p.get('img') and p['img'] != old_profile.get('img'):
            try:
                fresh=get(p['img'].replace('http:', 'https:'), True)
                photo=photo.with_suffix('.png');photo.write_bytes(fresh)
            except Exception as error:
                print(f'Portrait refresh deferred for {slug}: {error}',flush=True)
        if not photo.exists():
            try: photo.write_bytes(get(f'{ORIGIN}/stats/photos/{slug}.webp', True))
            except Exception:
                if p.get('img'):
                    photo = photo.with_suffix('.png')
                    photo.write_bytes(get(p['img'].replace('http:', 'https:'), True))
        if photo.exists(): p['photo'] = str(photo.relative_to(OUT))
        return slug,p
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(profile,s):s for s in slugs}
        for future in concurrent.futures.as_completed(futures):
            try:
                slug,p = future.result(); profiles[slug]=p
            except Exception as e: failures.append({'resource':futures[future],'error':str(e)})
    print('Profiles:',len(profiles),'failures:',failures,flush=True)
    assert all(p['u'] in profiles for p in event['players']), 'Missing Worlds profile'
    def team(slug):
        p=snapshot(f'hub/team/{slug}.json')
        dest=OUT/'assets'/'teams'/f'{slug}.webp'
        try:
            if not dest.exists():dest.write_bytes(get(f'{ORIGIN}/stats/logos/{slug}.webp',True))
        except Exception: pass
        return slug,{k:v for k,v in p.items() if k in ['n','u','code','c','name','region','league','img','logo','roster','country']} | {'logo':str(dest.relative_to(OUT)) if dest.exists() else None}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for slug,t in pool.map(team,[t['u'] for t in event['teams']]): teams[slug]=t
    # Keep the completed 2026 archive independent of the rolling /stats/worlds page.
    ids=sorted(previous.get('matches',{})) if previous else []
    if len(ids)!=event['series']:
        html=get(ORIGIN+'/tournament/worlds-2026',True).decode()
        ids=sorted(set(re.findall(r'/match/(worlds-2026-[a-z0-9-]+)',html)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for slug,match in pool.map(lambda s:(s,snapshot(f'hub/game/{s}.json')),ids):matches[slug]=match
    assert len(matches)==event['series'], f'Incomplete series: {len(matches)} != {event["series"]}'
    assert sum(len(m['games']) for m in matches.values())==event['games'], 'Incomplete game coverage'
    versions=get('https://ddragon.leagueoflegends.com/api/versions.json')
    dd=get(f'https://ddragon.leagueoflegends.com/cdn/{versions[0]}/data/en_US/champion.json')['data']
    champions={p['name']:key for key,p in dd.items()}
    names=set(c['c'] for p in profiles.values() for c in p.get('champs',[]))
    def champion(name):
        key=champions.get(name)
        if not key:return name,None
        dest=OUT/'assets'/'champions'/f'{key}.png'
        try:
            if not dest.exists():dest.write_bytes(get(f'https://ddragon.leagueoflegends.com/cdn/{versions[0]}/img/champion/{key}.png',True))
            return name,str(dest.relative_to(OUT))
        except Exception:return name,None
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: assets=dict(pool.map(champion,sorted(names)))
    data={'meta':{'title':'Worlds 2026','version':version,'built':latest['built'],'retrievedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'eventEnd':event['end'],'players':len(event['players']),'teams':len(event['teams']),'games':event['games'],'series':len(matches),'source':ORIGIN,'sourceSnapshot':base,'patch':versions[0],'failures':failures},'stages':stages,'profiles':profiles,'teams':teams,'matches':matches,'champions':assets}
    data['archive']={k:snapshot(path) for k,path in {
        'meta':'hub/meta.json','players':'hub/search/players.json','teams':'hub/search/teams.json',
        'events':'hub/search/events.json','photos':'hub/photos.json','logos':'hub/logos.json'}.items()}
    # Public CORS endpoints supply any historical profile, event or full game log on demand.
    # Cache the full logs of our initial profiles so common searches work offline too.
    (OUT/'history').mkdir(exist_ok=True)
    def history(slug):
        rows=snapshot(f'hub/playergames/{slug}.json')
        (OUT/'history'/f'{slug}.json').write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':')))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(history,profiles))
    validate_snapshot(data,previous)
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':'))
    tmp=OUT/'data.json.tmp';tmp.write_text(encoded);tmp.replace(OUT/'data.json')
    write_update_status(data)
    print(json.dumps({'profiles':len(profiles),'portraits':sum(bool(p.get('photo')) for p in profiles.values()),'games':event['games'],'series':len(matches),'bytes':len(encoded.encode()),'sha256':hashlib.sha256(encoded.encode()).hexdigest()},ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--force',action='store_true',help='Download the full snapshot even when its version is unchanged')
    main(force=parser.parse_args().force)
