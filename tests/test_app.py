import os
os.environ['DATABASE_PATH']='/tmp/hausmonitor-v31-test.db';os.environ['UPLOAD_DIR']='/tmp/hausmonitor-v31-uploads';os.environ['APP_PASSWORD']=''
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db,DB_PATH

def setup_module():
 if DB_PATH.exists():DB_PATH.unlink()
 init_db()

def test_health():
 with TestClient(app) as c: assert c.get('/health').json()['version']=='3.1.0'

def test_crack_flow():
 with TestClient(app) as c:
  r=c.post('/cracks',data={'name':'Riss Ost','location':'Wohnzimmer'},follow_redirects=False); assert r.status_code==303
  pid=r.headers['location'].split('/')[-1]
  r=c.post(f'/cracks/{pid}/measurements',data={'measured_at':'2026-10-02T20:00','air_temp':'18.5','value':'0.42','notes':'Start'},files={'photo':('riss.jpg',b'fakejpg','image/jpeg')},follow_redirects=False); assert r.status_code==303
  page=c.get(f'/cracks/{pid}'); assert '0.420 mm' in page.text and 'Riss Ost' in page.text
  assert c.get('/cracks-export.csv').status_code==200
