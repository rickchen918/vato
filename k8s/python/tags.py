import requests,json,base64,paramiko,pdb,yaml,os

with open("../answer.yml") as config:
    var=yaml.load(config)

mgr=var['nsxmgr']['ip']
mgruser=var['common']['user']
mgrpasswd=var['common']['password']
cred=base64.b64encode('%s:%s'%(mgruser,mgrpasswd))
header={"Authorization":"Basic %s"%cred,"Content-type":"application/json"}

overlaylsw=var['k8overlay']['lswname']
k8cluster=var['tags']['tag']

####### list logical switch #######
ep="/api/v1/logical-switches"
url="https://"+str(mgr)+str(ep)
conn=requests.get(url,verify=False,headers=header)
result=json.loads(conn.text).get('results')

for x in result:
    name=x.get('display_name')
    if name == overlaylsw:
	uuid=x.get('id')
    else:
	pass

####### list k8s logical port #######
ep="/api/v1/logical-ports"
url="https://"+str(mgr)+str(ep)
conn=requests.get(url,verify=False,headers=header)
result=json.loads(conn.text).get('results')

matrix=[]


for x in result:
    lswid=x.get('logical_switch_id')
    if lswid==uuid and x['attachment']['attachment_type']=='VIF': 
	portid=x.get('id')
        matrix.append(portid)    

print matrix	    
####### tagging logical port  #######
for x in matrix:
    ep="/api/v1/logical-ports/%s"%x
    url="https://"+str(mgr)+str(ep)
    conn=requests.get(url,verify=False,headers=header)
    name=json.loads(conn.text).get('display_name')
    vifname=name.split('/')[0]
    nic=json.loads(conn.text)['attachment']['attachment_type']
    vifid=json.loads(conn.text)['attachment']['id']
    revision=json.loads(conn.text).get('_revision')

    body="""
        {
	"display_name": "%s",
        "logical_switch_id": "%s",
        "_revision": %s,
        "admin_state": "UP",
	"attachment":{
	    "attachment_type":"%s",
	    "id":"%s"
	},
        "tags": [
        {
            "scope": "ncp/node_name",
            "tag": "%s"
        },
        {
            "scope": "ncp/cluster",
            "tag": "%s"
        }
        ]}"""%(name,uuid,revision,nic,vifid,vifname,k8cluster)
    print body
    
    conn1=requests.put(url,verify=False,headers=header,data=body)
    print conn1.text
