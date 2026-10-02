from __future__ import annotations
import csv,hmac,io,os,shutil,uuid
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI,Form,HTTPException,Request,UploadFile,File
from fastapi.responses import HTMLResponse,RedirectResponse,StreamingResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from .database import connection,init_db
from .analytics import campaign_stats,linear_trend

BASE=Path(__file__).resolve().parent; UPLOAD_DIR=Path(os.getenv('UPLOAD_DIR','/data/uploads')); POINTS=('SW','SO','ANB','TSW','TSO')
app=FastAPI(title='Hausmonitor',version='3.1.0'); app.add_middleware(SessionMiddleware,secret_key=os.getenv('SECRET_KEY','change-me'),https_only=os.getenv('COOKIE_SECURE','false').lower()=='true',same_site='lax')
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static'); templates=Jinja2Templates(directory=BASE/'templates')
@app.on_event('startup')
def startup(): init_db(); (UPLOAD_DIR/'cracks').mkdir(parents=True,exist_ok=True)
def auth(r): return not os.getenv('APP_PASSWORD','') or r.session.get('authenticated') is True
def guard(r): return None if auth(r) else RedirectResponse('/login',303)
def grouped(cid):
 d={p:[] for p in POINTS}
 with connection() as c:
  for x in c.execute('SELECT point,value FROM readings WHERE campaign_id=? ORDER BY sequence',(cid,)): d.setdefault(x['point'],[]).append(x['value'])
 return d
def campaigns():
 with connection() as c: rows=[dict(x) for x in c.execute('SELECT * FROM campaigns ORDER BY measured_at,id')]
 base=None; out=[]
 for row in rows:
  s=campaign_stats(grouped(row['id']),base)
  if base is None and s['tilt'] is not None: base=s['tilt']; s=campaign_stats(grouped(row['id']),base)
  row['stats']=s; out.append(row)
 return out
def crack_point(pid):
 with connection() as c:
  p=c.execute('SELECT * FROM crack_points WHERE id=?',(pid,)).fetchone(); ms=[dict(x) for x in c.execute('SELECT * FROM crack_measurements WHERE crack_point_id=? ORDER BY measured_at,id',(pid,))]
 if not p: raise HTTPException(404)
 return dict(p),ms
@app.get('/health')
def health(): return {'status':'ok','version':'3.1.0'}
@app.get('/login',response_class=HTMLResponse)
def login_page(request:Request): return templates.TemplateResponse(request=request,name='login.html',context={'error':None})
@app.post('/login')
def login(request:Request,password:str=Form(...)):
 if not os.getenv('APP_PASSWORD','') or hmac.compare_digest(password,os.getenv('APP_PASSWORD','')): request.session['authenticated']=True; return RedirectResponse('/',303)
 return templates.TemplateResponse(request=request,name='login.html',context={'error':'Passwort ist falsch.'},status_code=401)
@app.post('/logout')
def logout(request:Request): request.session.clear(); return RedirectResponse('/login',303)
@app.get('/',response_class=HTMLResponse)
def dashboard(request:Request):
 if (r:=guard(request)): return r
 cs=campaigns(); latest=cs[-1] if cs else None
 chart=[{'date':c['measured_at'],'delta':c['stats']['delta'],'se':c['stats']['combined_se']} for c in cs]
 with connection() as con: crack_count=con.execute('SELECT COUNT(*) FROM crack_points WHERE active=1').fetchone()[0]
 return templates.TemplateResponse(request=request,name='dashboard.html',context={'campaigns':list(reversed(cs)),'latest':latest,'chart':chart,'crack_count':crack_count})
@app.get('/campaigns/new',response_class=HTMLResponse)
def new_campaign(request:Request):
 if (r:=guard(request)): return r
 return templates.TemplateResponse(request=request,name='campaign_form.html',context={'now':datetime.now().strftime('%Y-%m-%dT%H:%M')})
@app.post('/campaigns')
def create_campaign(request:Request,measured_at:str=Form(...),air_temp:float|None=Form(None),wall_temp_sw:float|None=Form(None),wall_temp_so:float|None=Form(None),groundwater:float|None=Form(None),weather:str=Form(''),light_mode:str=Form(''),notes:str=Form('')):
 if (r:=guard(request)): return r
 with connection() as c: cid=c.execute('INSERT INTO campaigns(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,weather,light_mode,notes) VALUES(?,?,?,?,?,?,?,?)',(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,weather,light_mode,notes)).lastrowid
 return RedirectResponse(f'/campaigns/{cid}/readings',303)
@app.get('/campaigns/{cid}/readings',response_class=HTMLResponse)
def readings_form(request:Request,cid:int):
 if (r:=guard(request)): return r
 with connection() as c: row=c.execute('SELECT * FROM campaigns WHERE id=?',(cid,)).fetchone()
 if not row: raise HTTPException(404)
 return templates.TemplateResponse(request=request,name='readings_form.html',context={'campaign':dict(row),'points':POINTS,'existing':grouped(cid)})
@app.post('/campaigns/{cid}/readings')
async def save_readings(request:Request,cid:int):
 if (r:=guard(request)): return r
 form=await request.form()
 with connection() as c:
  c.execute('DELETE FROM readings WHERE campaign_id=?',(cid,))
  for p in POINTS:
   seq=0
   for raw in form.getlist(p):
    raw=str(raw).strip().replace(',','.')
    if raw: seq+=1; c.execute('INSERT INTO readings(campaign_id,point,sequence,value) VALUES(?,?,?,?)',(cid,p,seq,float(raw)))
 return RedirectResponse(f'/campaigns/{cid}',303)
@app.get('/campaigns/{cid}',response_class=HTMLResponse)
def campaign_detail(request:Request,cid:int):
 if (r:=guard(request)): return r
 c=next((x for x in campaigns() if x['id']==cid),None)
 if not c: raise HTTPException(404)
 return templates.TemplateResponse(request=request,name='campaign_detail.html',context={'campaign':c,'readings':grouped(cid)})
@app.get('/cracks',response_class=HTMLResponse)
def cracks(request:Request):
 if (r:=guard(request)): return r
 with connection() as c:
  rows=[dict(x) for x in c.execute('''SELECT p.*,COUNT(m.id) measurement_count,MAX(m.measured_at) last_date,(SELECT value FROM crack_measurements z WHERE z.crack_point_id=p.id ORDER BY measured_at DESC,id DESC LIMIT 1) last_value FROM crack_points p LEFT JOIN crack_measurements m ON m.crack_point_id=p.id GROUP BY p.id ORDER BY p.name''')]
 return templates.TemplateResponse(request=request,name='cracks.html',context={'points':rows})
@app.get('/cracks/new',response_class=HTMLResponse)
def new_crack(request:Request):
 if (r:=guard(request)): return r
 return templates.TemplateResponse(request=request,name='crack_point_form.html',context={})
@app.post('/cracks')
def create_crack(request:Request,name:str=Form(...),location:str=Form(''),description:str=Form('')):
 if (r:=guard(request)): return r
 try:
  with connection() as c: pid=c.execute('INSERT INTO crack_points(name,location,description) VALUES(?,?,?)',(name,location,description)).lastrowid
 except Exception as e:
  raise HTTPException(400,'Name bereits vorhanden') from e
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/cracks/{pid}',response_class=HTMLResponse)
def crack_detail(request:Request,pid:int):
 if (r:=guard(request)): return r
 p,ms=crack_point(pid); baseline=ms[0]['value'] if ms else None
 for m in ms: m['delta']=m['value']-baseline if baseline is not None else None
 chart=[{'date':m['measured_at'],'value':m['value'],'delta':m['delta'],'temp':m['air_temp']} for m in ms]
 return templates.TemplateResponse(request=request,name='crack_detail.html',context={'point':p,'measurements':list(reversed(ms)),'chart':chart,'trend':linear_trend(ms)})
@app.get('/cracks/{pid}/measurements/new',response_class=HTMLResponse)
def new_crack_measurement(request:Request,pid:int):
 if (r:=guard(request)): return r
 p,_=crack_point(pid)
 return templates.TemplateResponse(request=request,name='crack_measurement_form.html',context={'point':p,'now':datetime.now().strftime('%Y-%m-%dT%H:%M')})
@app.post('/cracks/{pid}/measurements')
async def create_crack_measurement(request:Request,pid:int,measured_at:str=Form(...),air_temp:float|None=Form(None),value:float=Form(...),notes:str=Form(''),photo:UploadFile|None=File(None)):
 if (r:=guard(request)): return r
 crack_point(pid); photo_path=None
 if photo and photo.filename:
  ext=Path(photo.filename).suffix.lower() if Path(photo.filename).suffix else '.jpg'; filename=f'{pid}-{uuid.uuid4().hex}{ext}'; target=UPLOAD_DIR/'cracks'/filename
  with target.open('wb') as f: shutil.copyfileobj(photo.file,f)
  photo_path=filename
 with connection() as c: c.execute('INSERT INTO crack_measurements(crack_point_id,measured_at,air_temp,value,photo_path,notes) VALUES(?,?,?,?,?,?)',(pid,measured_at,air_temp,value,photo_path,notes))
 return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/crack-photos/{filename}')
def crack_photo(request:Request,filename:str):
 if (r:=guard(request)): return r
 safe=Path(filename).name; path=UPLOAD_DIR/'cracks'/safe
 if not path.exists(): raise HTTPException(404)
 return FileResponse(path)
@app.post('/cracks/{pid}/delete')
def delete_crack(request:Request,pid:int):
 if (r:=guard(request)): return r
 p,ms=crack_point(pid)
 for m in ms:
  if m['photo_path']:
   try:(UPLOAD_DIR/'cracks'/m['photo_path']).unlink()
   except FileNotFoundError:pass
 with connection() as c:c.execute('DELETE FROM crack_points WHERE id=?',(pid,))
 return RedirectResponse('/cracks',303)
@app.get('/cracks-export.csv')
def cracks_export(request:Request):
 if (r:=guard(request)): return r
 out=io.StringIO(); w=csv.writer(out,delimiter=';'); w.writerow(['Messstelle','Ort','Datum','Lufttemperatur','Messwert','Notiz','Foto'])
 with connection() as c:
  for x in c.execute('''SELECT p.name,p.location,m.measured_at,m.air_temp,m.value,m.notes,m.photo_path FROM crack_measurements m JOIN crack_points p ON p.id=m.crack_point_id ORDER BY p.name,m.measured_at'''): w.writerow(list(x))
 return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=rissmonitoring.csv'})
