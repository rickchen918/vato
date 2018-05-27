import tlr
import json,yaml,argparse
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

with open('../answer.yml') as config:
    info=yaml.load(config)
overlaylsw=info['k8overlay']['lswname']
mgmtlsw=info['k8mgmt']['lswname']
scope=info['tags']['scope']
tag=info['tags']['tag']

# set target lsw name for filter
lswname=overlaylsw

# get lsw uuid by lsw name filter
getlsw=json.loads(tlr.get_lsw()).get('results')
#print getlsw

for x in getlsw:
    if x['display_name']==overlaylsw:
	lswid=x.get('id')
#        print " the LSW UUID found "+ str(lswid)
    else:
	pass

# searching the lport whihc has no tag setting 
getlport=json.loads(tlr.get_lswport()).get('results')
# print tlr.get_lswport()

lport_m=[]

	# if lport matching lsw uuid + type vif + no tag related, upon this condition to build lport list
for x in getlport:
    if x.get('logical_switch_id')==lswid and x['attachment']['attachment_type']=='VIF' and ('tags' not in x or x.get('tags') == []):
	lportid=x.get('id')
#        print lportid
	lport_m.append(lportid)
    else: 
        pass

for x in lport_m:
    body=json.loads(tlr.get_lswportid(x))
    vifname=body['display_name'].split('/')[0]
    k8scluster="rkc_cluster"
    del body["_create_time"]
    del body["_create_user"]
    del body["_last_modified_time"]
    del body["_last_modified_user"]
    del body["_protection"]
    del body["_system_owned"]
    newtag=json.loads("""{"tags" : [ {"scope" : "ncp/cluster","tag" : "%s"}, {"scope" : "ncp/node_name","tag" : "%s"} ]}"""%(k8scluster,vifname))
    body.update(newtag)
    newbody=json.dumps(body)
    tlr.update_lport(x,newbody)

