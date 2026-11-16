"""Package only public runtime files; never publish Git, CI, or source cache files."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist' if (ROOT/'dist'/'index.html').exists() else ROOT
TARGET=ROOT/'.site'
if TARGET.exists():shutil.rmtree(TARGET)
TARGET.mkdir()
for name in ['index.html','app.js','model.js','freshness.js','styles.css','data.json','asset-overrides.json','update.json']:
    shutil.copy2(OUT/name,TARGET/name)
for name in ['assets','history']:shutil.copytree(OUT/name,TARGET/name)
(TARGET/'.nojekyll').touch()
print('Packaged runtime files into',TARGET)
