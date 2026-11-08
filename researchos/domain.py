"""Scoped synthetic domain adapter; no external execution."""
import math

def winding(t1,t2,n):
    angles=[math.atan2(t2*math.sin(2*math.pi*i/n),t1+t2*math.cos(2*math.pi*i/n)) for i in range(n)]
    return sum(math.atan2(math.sin(angles[(i+1)%n]-a),math.cos(angles[(i+1)%n]-a)) for i,a in enumerate(angles))/(2*math.pi)

def check():
    observed=[{'t1':t1,'t2':1,'winding_128':winding(t1,1,128),'winding_256':winding(t1,1,256)} for t1 in (0.5,2)]
    passed=all(abs(r['winding_128']-expected)<1e-10 and abs(r['winding_256']-expected)<1e-10 for r,expected in zip(observed,(1,0)))
    return {'domain':'physics-materials','statement':'The supplied gapped two-band SSH winding fixtures evaluate to 1 and 0 at two sampling resolutions.',
            'passed':passed,'configuration':{'complex_curve':'t1 + t2 exp(ik)','parameters':[[0.5,1],[2,1]],'samples':[128,256]},
            'observed':observed,'scope':'Synthetic mathematical band-model check; no real material validation or gapless-case claim'}
