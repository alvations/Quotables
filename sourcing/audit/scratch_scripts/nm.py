import re,sys
def name(title,pid):
    t=re.sub(r"[^A-Za-z0-9 ',-]","",title)
    t=re.sub(r"[ ',-]+","-",t)
    m=99-len(str(pid))-1
    if len(t)>m: return t[:m]+"__"+str(pid)
    return t+"_"+str(pid)
for line in sys.stdin:
    line=line.rstrip("\n")
    if not line.strip(): continue
    title,pid=line.rsplit("\t",1)
    print(name(title,pid))
