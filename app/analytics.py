from math import sqrt
from statistics import mean,stdev

def summarize(values):
 if not values:return {'n':0,'mean':None,'sd':None,'se':None,'range':None}
 sd=stdev(values) if len(values)>1 else None
 return {'n':len(values),'mean':mean(values),'sd':sd,'se':sd/sqrt(len(values)) if sd is not None else None,'range':max(values)-min(values)}

def campaign_stats(grouped,baseline=None):
 out={p:summarize(v) for p,v in grouped.items()}; sw=out.get('SW',{}); so=out.get('SO',{})
 tilt=combined=delta=snr=None; quality='unvollständig'
 if sw.get('mean') is not None and so.get('mean') is not None:
  tilt=so['mean']-sw['mean']
  if sw.get('se') is not None and so.get('se') is not None: combined=sqrt(sw['se']**2+so['se']**2)
  if baseline is not None:
   delta=tilt-baseline
   if combined and combined>0:
    snr=abs(delta)/combined; quality='Signal klar' if snr>=3 else 'Hinweis' if snr>=2 else 'im Rauschen'
   else: quality='nicht bewertbar'
 out.update(tilt=tilt,combined_se=combined,delta=delta,snr=snr,quality=quality)
 return out

def linear_trend(rows):
 pts=[(i,float(r['value'])) for i,r in enumerate(rows)]
 if len(pts)<2:return None
 n=len(pts); sx=sum(x for x,_ in pts); sy=sum(y for _,y in pts); sxx=sum(x*x for x,_ in pts); sxy=sum(x*y for x,y in pts)
 den=n*sxx-sx*sx
 return (n*sxy-sx*sy)/den if den else None
