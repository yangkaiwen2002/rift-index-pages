"""Verify the exact published release anonymously, with bounded CDN propagation retries."""
import hashlib,json,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist' if (ROOT/'dist'/'index.html').exists() else ROOT
expected=json.loads((OUT/'update.json').read_text())
base='https://yangkaiwen2002.github.io/rift-index-pages/'
for attempt in range(12):
    try:
        nonce=str(time.time_ns())
        with urllib.request.urlopen(base+'update.json?t='+nonce,timeout=30) as r:actual=json.load(r)
        if actual['checkedAt']!=expected['checkedAt'] or actual['dataSha256']!=expected['dataSha256']:
            raise ValueError('CDN is still serving an earlier release')
        with urllib.request.urlopen(base+'data.json?v='+actual['sourceVersion']+'&t='+nonce,timeout=60) as r:payload=r.read()
        if hashlib.sha256(payload).hexdigest()!=expected['dataSha256']:
            raise ValueError('Published dataset does not match the validated artifact')
        with urllib.request.urlopen(base+'?t='+nonce,timeout=30) as r:
            if r.status!=200:raise ValueError('Public homepage unavailable')
        print('Verified public deployment:',actual['sourceVersion'],actual['checkedAt'])
        break
    except Exception as error:
        print(f'Propagation check {attempt+1}/12: {error}',flush=True)
        if attempt==11:raise
        time.sleep(10)
