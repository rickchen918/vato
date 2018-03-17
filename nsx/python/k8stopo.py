import tlr,requests,json,base64,pdb,yaml,os
print os.getcwd()

# import answer.yml to create overlay logical switch for container vm host 
with open('../answer.yml') as config:
    info=yaml.load(config)
overlaylsw=info['k8overlay']['lswname']
mgmtlsw=info['k8mgmt']['lswname']
scope=info['tags']['scope']
tag=info['tags']['tag']

### create transport zone ###
# create overlay transport zone 
overlay=tlr.create_transportzone("overlay","overlay","OVERLAY")
# create vlan transport zone 
vlan=tlr.create_transportzone("vlan","vlan","VLAN")

### create requirement of edge node registration 
# create uplink profil for edge 
edge_uplinkprofile=tlr.create_uplinkprofile("edge_uplinkprofile","1600","0")
# create ip pool for transport node 
pool=tlr.create_ipool("tep","192.168.0.96","192.168.65.100","192.168.65.254","192.168.65.1","192.168.65.0/24")
# retrieve edge node uuid
edgenodeid=tlr.edgenodeid()
# retrieve transport node id 
transportnodeid=tlr.transportnodeid()

### scan edge node to look for the node which is not added into transport node yet and register to transport node ###
tn_matrix=[]
edge_matrix=[]
# retrieve value from key:value pair into list
for x,y in transportnodeid.iteritems():
    tn_matrix.append(y)

for x,y in edgenodeid.iteritems():
    edge_matrix.append(y)

# if edge nodeid in the transport nodeid, remove from list     
for y in tn_matrix:
    for x in edge_matrix:
	if x in y:
	    edge_matrix.remove(x)
	
# register edge node to transport node 
for x in edge_matrix:
    tlr.create_edgetransportnode(x,edge_uplinkprofile,"vlan","fp-eth1","overlay","fp-eth0",pool,vlan,overlay,x)

### edge cluster initialization ###
# retrieve edge cluster profile uuid (EdgeHighAvailabilityProfile)
edgeclusterprofile=tlr.edgeclusterprofile()

# create additional call to have member list from edge_matrix (becuase edge transport node uuid is copied from edge node uuid)
# the member list is placed on body to for member info requirement 
# eg:"members": [{"transport_node_id": "6102f104-f027-11e7-bb7e-005056a641c0"}, {"transport_node_id": "cbeac596-f027-11e7-8a22-005056a6fdbc"}]
member_matrix=[]
for x in edge_matrix:
    pair={'transport_node_id':str(x)}
    member_matrix.append(pair)
# due to nsx-t only accept json with double quote, it has to be converted by json dumps
member=json.dumps(member_matrix)
edgeclusterid=tlr.create_edgecluster("edgecluster",edgeclusterprofile,member)
print edgeclusterid

# create vlan logicalswitch1
#vlanlsw1=tlr.create_vlanlsw(vlan,"vlanlsw1","0")
#lp1lsw1=tlr.create_lswport("lsw1p1",vlanlsw1)

#vlanlsw2=tlr.create_vlanlsw(vlan,"vlanlsw2","0")
#lp1sw2=tlr.create_lswport("lsw2p1",vlanlsw2)

# create overlay logical switch 
k8mgmt=tlr.create_overlaylsw(overlay,"%s"%mgmtlsw)
k8overlay=tlr.create_overlaylsw(overlay,"%s"%overlaylsw)

# create overlay logical switch port 
k8mgmtport=tlr.create_lswport("to_router",k8mgmt)
k8overlayport=tlr.create_lswport("to_router",k8overlay)

# update k8s cluster tag to overlay logical switch
tlr.update_tag_lsw(k8overlay)

# create logical T0 router 
t0=tlr.create_lr0("k8t0","TIER0","ACTIVE_STANDBY",edgeclusterid)

# create logical T0 donwlink
t0_downmgt=tlr.create_lr0downlink(t0,k8mgmtport,"192.168.100.1","24")
t0_downoverlay=tlr.create_lr0downlink(t0,k8overlayport,"192.168.101.1","24")

# create ip block for k8s namespace 
k8block=tlr.create_ipblock("k8ipblock","192.168.102.0/24")

# create nat pool and update tag for k8s
natpool=tlr.create_ipool("natpool","192.168.0.96","192.168.102.100","192.168.102.199","192.168.102.1","192.168.102.0/24")
body=tlr.get_ipool_body(natpool)
matrix=[]
for x in body:
    if ("_create_" in x) or ("_last_" in x) or ("_system_" in x) or ("_protection" in x):
	 matrix.append(x)

for y in matrix:
	del body[y]

new=json.loads("""{"tags" : [ {"scope" : "ncp/external","tag" : "true"}, {"scope" : "%s","tag" : "%s"} ]}"""%(tlr.scope,tlr.tag))
body.update(new)
newbody=json.dumps(body)
tlr.put_ipool_body(natpool,newbody)
