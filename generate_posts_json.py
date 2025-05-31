import os,json,re
posts=[]
for html in sorted([p for p in os.listdir('posts') if os.path.isdir(os.path.join('posts',p))]):
    path=os.path.join('posts',html,'index.html')
    with open(path) as f:
        data=f.read()
    m=re.search(r'<title>(.*?)</title>',data)
    title=m.group(1) if m else html
    posts.append({'title':title,'path':path})
with open('posts.json','w') as f:
    json.dump(posts,f,indent=2)
