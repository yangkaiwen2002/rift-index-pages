"""Package only public runtime files; never publish Git, CI, or source cache files."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist' if (ROOT/'dist'/'index.html').exists() else ROOT
TARGET=ROOT/'.site'
if TARGET.exists():shutil.rmtree(TARGET)
TARGET.mkdir()
for name in ['index.html','app.js','model.js','freshness.js','match-model.js','match-index.json','styles.css','data.json','asset-overrides.json','update.json']:
    shutil.copy2(OUT/name,TARGET/name)
for name in ['assets','history','matches']:shutil.copytree(OUT/name,TARGET/name)
(TARGET/'.nojekyll').touch()
print('Packaged runtime files into',TARGET)

# Fingerprint JS imports and entrypoints so an updated HTML file cannot load stale code.
import hashlib,re
def digest(name):return hashlib.sha256((TARGET/name).read_bytes()).hexdigest()[:16]
app=(TARGET/'app.js').read_text()
for name in ['model.js','freshness.js','match-model.js']:
    app=app.replace("'./"+name+"'","'./"+name+"?v="+digest(name)+"'")
(TARGET/'app.js').write_text(app)
html=(TARGET/'index.html').read_text()
for name in ['app.js','styles.css']:
    html=re.sub(re.escape(name)+r'(?:\?[^"\s]*)?',name+'?v='+digest(name),html)
(TARGET/'index.html').write_text(html)
