import requests,json,base64,paramiko,pdb,yaml,os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
# refer var from yaml de./nsxt_answer.yml")
with open("../answer.yml") as config:
    var=yaml.load(config)

mgr=var['nsxmgr']['ip']
#mgruser="adMin"
mgruser=var['common']['user']
mgrpasswd=var['common']['password']
cred=base64.b64encode('%s:%s'%(mgruser,mgrpasswd))
header={"Authorization":"Basic %s"%cred,"Content-type":"application/json"}
scope=var['tags']['scope']
tag=var['tags']['tag']

### transport zone section ###
# create k8s overlay transport zone, the var of functions are 
# name: transport zone name 
# hostswitch: hostswitch name of transport zone requirment 
# tntype: "Overlay" or "VLAN"
# scope: under Tags
# tag: under tags
def create_transportzone(name,hostswitch,tntype):
    ep="/api/v1/transport-zones"
    url="https://"+str(mgr)+str(ep)
    body="""{
    "display_name":"%s",
    "host_switch_name":"%s",
    "description":"",
    "transport_type":"%s",
    "tags": [
    {
    "scope" : "%s",                                                     
    "tag" : "%s"  
    }
    ]
    }"""%(name,hostswitch,tntype,scope,tag)
    conn=requests.post(url,verify=False,headers=header,data=body)
    if conn.status_code == 201:
        uuid=json.loads(conn.text).get('id')
        name=json.loads(conn.text).get('display_name')
        print "the transport zone "+str(name)+" "+str(uuid)+" has been sucessfully created" 
        return uuid
    else:
        print "the create transport zone "+str(name)+" is failed"
        print "the return code is "+str(conn.status_code)
        quit()

#vlan traansport zone uuid retreive
def tz_id():
    eptz="/api/v1/transport-zones"
    url="https://"+str(mgr)+str(eptz)
    conn=requests.get(url,verify=False,headers=header)
    if conn.status_code == 200:
        data=json.loads(conn.text)
        result=data.get('results')
        matrix={}
    else:
    	print "the return code is "+str(conn.status_code)
        quit()

    for x in result:
        Type=x.get('transport_type')
        uuid=x.get('id')
        pair={Type:uuid}
        matrix.update(pair)
    return matrix

### transport node section ###
# IP Pool creation 
# name: Pool name
# dns: dns servers
# start: ip range starting 
# end: ip range ending 
# gw: gateway address
# cidr: subnet of ip range eg: 192.168.65.0/24
def create_ipool(name,dns,start,end,gw,cidr):
    ep="/api/v1/pools/ip-pools"                                                                                   
    url="https://"+str(mgr)+str(ep)
    body="""{
	 "display_name": "%s",
 	 "description": "",
  	 "subnets": [
    	  {
           "dns_nameservers": ["%s"],
           "allocation_ranges": [
            {
             "start": "%s",
             "end": "%s"
            }
            ],
          "gateway_ip": "%s",
          "cidr": "%s"
           }
           ]
           }"""%(name,dns,start,end,gw,cidr)
    conn=requests.post(url,verify=False,headers=header,data=body)                                                                     
    result=json.loads(conn.text)                                                                                        
    if conn.status_code==201:
       result=json.loads(conn.text)
       uuid=result.get('id')
       name=result.get('display_name')
       print "the ip pool "+str(name)+" "+str(uuid)+" has been sucessfully created"
       return uuid 
    else:                                                                                                               
        print "the return code is "+str(conn.status_code)
        quit()

# get ip pool body
def get_ipool_body(poolid):
    ep="/api/v1/pools/ip-pools/%s"%poolid
    url="https://"+str(mgr)+str(ep)
    conn=requests.get(url,verify=False,headers=header)   
    if conn.status_code==200:
       result=json.loads(conn.text)
       return result
    else:
       print "the return code is "+str(conn.status_code)
       quit()

# update ip pool configuration 
def put_ipool_body(poolid,body):
    ep="/api/v1/pools/ip-pools/%s"%poolid
    url="https://"+str(mgr)+str(ep) 
    conn=requests.put(url,verify=False,headers=header,data=body)  
    if conn.status_code==200:
       result=json.loads(conn.text)            
       return result
    else:        
        print "the return code is "+str(conn.status_code)
        quit()

# create uplink profile, aka host-switch-profile 
# name: profile name
# mtu: uplink mtu size
# vlan: uplink vlan tag, default is 0
def create_uplinkprofile(name,mtu,vlan):
    ep="/api/v1/host-switch-profiles"
    url="https://"+str(mgr)+str(ep)
    body="""{
    "resource_type": "UplinkHostSwitchProfile",
    "display_name": "%s",
    "mtu": "%s",
    "teaming": {
       "active_list": [
         {
             "uplink_name": "uplink-1",
             "uplink_type": "PNIC"
         }
       ],
       "policy": "FAILOVER_ORDER"
     },
     "transport_vlan": "%s"
     }"""%(name,mtu,vlan)
    conn=requests.post(url,verify=False,headers=header,data=body)                                                                  
    result=json.loads(conn.text)
    if conn.status_code==201:
        matrix={}
        uuid=result.get('id')                                                                                              
        return uuid                                                                                              
    else:                                                                                                           
        print "the return code is "+str(conn.status_code)        
        quit()

# edge node uuid retrieve 
def edgenodeid():
    ep="/api/v1/fabric/nodes?resource_type=EdgeNode"
    url="https://"+str(mgr)+str(ep)
    conn=requests.get(url,verify=False,headers=header)
    result=json.loads(conn.text).get('results')
    if conn.status_code==200:
        matrix={}
        for x in result:
	    name=x.get('display_name')
            uuid=x.get('id')
            pair={name:uuid}
            matrix.update(pair)
        return matrix
    else:
        print "the return code is "+str(conn.status_code)
        quit()

# register edge node to transport node
# name: transport name
# uplinkprofile: the uuid of uplinkprofile under fabric 
# vlanhswname: the vlan hostswitch name in transport zone 
# fpeth1: design for vlan interface on fp-eth1, it can be changed to other interface name
# overlayhswname: the overlay hostswitch name in transport node 
# fpeth0: design for tunnel interface on fp-eth0, it can be changed to other interface name
# pool: the uuid of ip pool for tunnel interface 
# vlantzid: the uuid of vlan transport zone 
# overlaytzid: the uuid of overlay transport zone
# nodeid: the uuid of edge node  
def create_edgetransportnode(name,uplinkprofile,vlanhswname,fpeth1,overlayhswname,fpeth0,pool,vlantzid,overlaytzid,nodeid):
    ep="/api/v1/transport-nodes"
    url="https://"+str(mgr)+str(ep)
    body="""{
    "resource_type": "TransportNode",
    "display_name": "%s", 
    "host_switch_spec": {
        "resource_type": "StandardHostSwitchSpec",
        "host_switches": [
            {
                "host_switch_profile_ids": [
                    {
                        "value": "%s",
                        "key": "UplinkHostSwitchProfile"
                    }
                ],
                "host_switch_name": "%s",
                "pnics": [
                    {
                        "device_name": "%s",
                        "uplink_name": "uplink-1"
                    }
                ],
                "ip_assignment_spec": {
                    "resource_type": "AssignedByDhcp"
                },
                "cpu_config": []
            },
            {
                "host_switch_profile_ids": [
                    {
                        "value": "%s",
                        "key": "UplinkHostSwitchProfile"
                    }
                ],
                "host_switch_name": "%s",
                "pnics": [
                    {
                        "device_name": "%s",
                        "uplink_name": "uplink-1"
                    }
                ],
                "ip_assignment_spec": {
                    "resource_type": "StaticIpPoolSpec",
                    "ip_pool_id": "%s"
                },
                "cpu_config": []
            }
        ]
    },
    "transport_zone_endpoints": [
        {
            "transport_zone_id": "%s"
        },
        {
            "transport_zone_id": "%s"
        }
    ],
    "node_id": "%s"}"""%(name,uplinkprofile,vlanhswname,fpeth1,uplinkprofile,overlayhswname,fpeth0,pool,vlantzid,overlaytzid,nodeid)
    conn=requests.post(url,verify=False,headers=header,data=body)
    if conn.status_code==201:
	print "the edge "+str(name)+" has been created for transport node"
    else:
        print "the edge "+str(name)+" has NOT been created for transport node"
        quit()

# output is key pair of transport node display name and uuid 
def transportnodeid():
    ep="/api/v1/transport-nodes"                                                                                          
    url="https://"+str(mgr)+str(ep)                                                                                     
    conn=requests.get(url,verify=False,headers=header)   
    result=json.loads(conn.text).get('results')
    if conn.status_code==200:
	matrix={}
	for x in result:
	    name=x.get('display_name')
	    uuid=x.get('id')
	    pair={name:uuid}
	    matrix.update(pair)
    	return matrix
    else:
    	print "the return code is "+str(conn.status_code)
        quit()

# retrive transport node body return
def transportnode():                                                                                                  
    ep="/api/v1/transport-nodes"                                                                                          
    url="https://"+str(mgr)+str(ep)                                                                                     
    conn=requests.get(url,verify=False,headers=header)                                                                  
    result=json.loads(conn.text).get('results') 
    return result


### edge section ###
# the context of members of body is input from external loop to generate the transport node uuid and fill 
# create edge cluster without memeber
# name: edge cluster name 
# edgeclusterprofile: uuid of edgeclusterprofile, it can be acquired from function of "def edgeclusterprofile()"
# transportnodeidjson: the context of members of json body generation from exteranl loop, it desires to detect number of 
# edge nodes being on transport node and create dictionary for memebership context
def create_edgecluster(name,edgeclusterprofile,transportnodeidjson):
    ep="/api/v1/edge-clusters"
    url="https://"+str(mgr)+str(ep)
    body="""{
    "display_name": "%s",
    "cluster_profile_bindings": [
    {
        "profile_id":"%s",
        "resource_type": "EdgeHighAvailabilityProfile"
    }
    ],
    "members": %s
    }"""%(name,edgeclusterprofile,transportnodeidjson)
    conn=requests.post(url,verify=False,headers=header,data=body)
    if conn.status_code==201:
	result=json.loads(conn.text)
    	uuid=result.get('id')
        print "the edge cluster "+str(uuid)+" has been created sucessfully"
        return uuid
    else:
        print "create_edgecluster is failed"
        quit()

# edge cluster profile uuid retrieve
def edgeclusterprofile():
    ep="/api/v1/cluster-profiles?resource_type=EdgeHighAvailabilityProfile"
    url="https://"+str(mgr)+str(ep)
    conn=requests.get(url,verify=False,headers=header)
    result=json.loads(conn.text).get('results')
    for x in result:
        uuid=x.get('id')
        return uuid


# edge cluster uuid retrieve     
def edgeclusterid():
    ep="/api/v1/edge-clusters"
    url="https://"+str(mgr)+str(ep)
    conn=requests.get(url,verify=False,headers=header)
    result=json.loads(conn.text).get('results')
    for x in result:
        uuid=x.get('id')
        return uuid

# edgecluster revision uuid retrive 
# the revision is used for put action update
def edgeclusterrevision():
    ep="/api/v1/edge-clusters"                                                                                    
    url="https://"+str(mgr)+str(ep)                                                                               
    conn=requests.get(url,verify=False,headers=header)                                                            
    result=json.loads(conn.text).get('results')                                                                   
    for x in result:                                                                                              
        revision=x.get('_revision')                                                                                          
        return revision  

### logical switch section ### 
# create logical switch 
# tzid: vlan transport zone id 
# name: logical switch name 
# vlan: vlan tag id
def create_vlanlsw(tzid,name,vlan):
    ep="/api/v1/logical-switches"                                                                                        
    url="https://"+str(mgr)+str(ep)     
    body="""{
    "transport_zone_id": "%s",
    "replication_mode": "MTEP",
    "admin_state":"UP",
    "display_name":"%s",
    "vlan": "%s"
    }"""%(tzid,name,vlan)
    conn=requests.post(url,verify=False,headers=header,data=body)  
    if conn.status_code == 201:
        uuid=json.loads(conn.text).get('id')
        name=json.loads(conn.text).get('display_name')
        print "the logical switch "+str(name)+" "+str(uuid)+" has been sucessfully created" 
        return uuid
    else:
        print "the create logical switch "+str(name)+" is failed"
        print "the return code is "+str(conn.status_code)
        quit()

# create overlay lsw 
# tzid: vlan transport zone id 
# name: logical switch name 
def create_overlaylsw(tzid,name):
    ep="/api/v1/logical-switches"                                                                                        
    url="https://"+str(mgr)+str(ep)     
    body="""{
    "transport_zone_id": "%s",
    "replication_mode": "MTEP",
    "admin_state":"UP",
    "display_name":"%s"
    }"""%(tzid,name)
    conn=requests.post(url,verify=False,headers=header,data=body)  
    if conn.status_code == 201:
        uuid=json.loads(conn.text).get('id')
        name=json.loads(conn.text).get('display_name')
        print "the logical switch "+str(name)+" "+str(uuid)+" has been sucessfully created" 
        return uuid
    else:
        print "the create logical switch "+str(name)+" is failed"
        print "the return code is "+str(conn.status_code)
        quit()

# update logical port 
def update_lport(portid,update_body):
    ep="/api/v1/logical-ports/%s"%(portid)
    url="https://"+str(mgr)+str(ep)
    body=update_body
    conn=requests.put(url,verify=False,headers=header,data=body)
    if conn.status_code == 200:
	print portid+" is update"
    else: 
        print "the logical port update is failed"
        print conn.text


# update tags to logical switch 
def update_tag_lsw(lswuuid):
    ep="/api/v1/logical-switches/"+str(lswuuid)    
    url="https://"+str(mgr)+str(ep)
    conn=requests.get(url,verify=False,headers=header)
    if conn.status_code == 200:
	revision=json.loads(conn.text).get('_revision')
        tzid=json.loads(conn.text).get('transport_zone_id')
        name=json.loads(conn.text).get('display_name')
    else:
        print "the logical switch "+str(lswuuid)+" query is not sucessfully"
        print "the return code is "+str(conn.status_code)
        quit()
   
    body="""{
    "display_name": "%s",
    "transport_zone_id": "%s",
    "admin_state": "UP",
    "replication_mode": "MTEP",
    "tags":[
    {
  	"scope":"%s",
	"tag": "%s"
    }
    ],
    "_revision": "%s"
    }"""%(name,tzid,scope,tag,revision)
    conn=requests.put(url,verify=False,headers=header,data=body)
    if conn.status_code == 200:
        uuid=json.loads(conn.text).get('id')
        print "logical switch "+str(lswuuid)+" has been updated sucessfully"
    else:
	print "logical switch "+str(lswuuid)+" hasn't been updated sucessfully"
        print "the return code is "+str(conn.status_code)
        quit()

# create logical switch port 
def create_lswport(name,lswid):
    ep="/api/v1/logical-ports"
    url="https://"+str(mgr)+str(ep)
    body="""{
    "display_name": "%s",
    "logical_switch_id":"%s",
    "admin_state":"UP"
    }"""%(name,lswid)
    conn=requests.post(url,verify=False,headers=header,data=body)
    if conn.status_code == 201:
        uuid=json.loads(conn.text).get('id')
        name=json.loads(conn.text).get('display_name')
        print "the logical switch port "+str(uuid)+" has been sucessfully created"
        return uuid
    else:
        print "the create logical switch port "+str(name)+" is failed"
        print "the return code is "+str(conn.status_code)
        quit()

def get_lsw():
    ep="/api/v1/logical-switches"
    url="https://"+str(mgr)+str(ep)
    conn=requests.get(url,verify=False,headers=header)
    if conn.status_code == 200:                                                                                        
        return conn.text                                                                                               
    else:                                                                                                              
        print conn.text  

def get_lswport():
    ep="/api/v1/logical-ports"
    url="https://"+str(mgr)+str(ep)
    conn=requests.get(url,verify=False,headers=header)
    if conn.status_code == 200:
        return conn.text
    else:
        quit()

def get_lswportid(uuid):
    ep="/api/v1/logical-ports/%s"%(uuid)
    url="https://"+str(mgr)+str(ep)
    conn=requests.get(url,verify=False,headers=header)
    if conn.status_code == 200:
        return conn.text
	print conn.text
    else:
        print conn.text


### logical router section ###
# create T0 logical router, I do hard-code tag for testing 
# name: t0 router name 
# type: TIER0 or TIER1
# mode: ACTIVE_ACTIVE or ACTIVE_STANDBY
# esgid: Edge Cluster uuid  
def create_lr0(name,type0,mode0,esgid):
    ep="/api/v1/logical-routers"
    url="https://"+str(mgr)+str(ep)
    body="""{
            "resource_type": "LogicalRouter",
            "description": "",
            "display_name": "%s",
            "edge_cluster_id": "%s",
            "advanced_config": {
            "external_transit_networks": [
            "100.64.0.0/16"
             ],
            "internal_transit_network": "169.254.0.0/28"
             },
             "router_type": "%s",
             "high_availability_mode": "%s",
             "tags" : [                                                                                  
             {                                                                                           
             "scope" : "%s",                                                                    
             "tag" : "%s"                                                                         
             }                                                                                           
             ] 
             } """%(name,esgid,type0,mode0,scope,tag)
    conn=requests.post(url,verify=False,headers=header,data=body)
    if conn.status_code==201:
       uuid=json.loads(conn.text).get('id')
       print "The logical router "+str(uuid)+" has been created sucessfully"
       return uuid
    else:
       print "the result code is "+str(conn.status_code)+" not sucessfully"
       quit()

# create T0 logical router uplink 
def create_lr0uplink(lr0uuid,vlanlswport,subnet,member,length):
    ep="/api/v1/logical-router-ports"
    url="https://"+str(mgr)+str(ep)
    body="""{
        "resource_type": "LogicalRouterUpLinkPort",
        "logical_router_id": "%s",
        "linked_logical_switch_port_id":{
                "target_type": "LogicalPort",
                "target_id": "%s"
                },
        "edge_cluster_member_index":[
                %s
        ],
         "subnets": [
                {
                 "ip_addresses": [
                        "%s"
                ],
                 "prefix_length": "%s"
                }
                ]
        }"""%(lr0uuid,vlanlswport,member,subnet,length)
    conn=requests.post(url,verify=False,headers=header,data=body)
    result=json.loads(conn.text).get('id')
    if conn.status_code==201:
       uuid=json.loads(conn.text).get('id')
       print "The logical router port"+str(uuid)+" has been created sucessfully"
       return uuid
    else:
       print "the result code is "+str(conn.status_code)+" not sucessfully"
       quit()

# create T0 logical router downlink
def create_lr0downlink(lr0uuid,overlaylswport,ipaddr,length):                                                         
    ep="/api/v1/logical-router-ports"                                                                                   
    url="https://"+str(mgr)+str(ep)                                                                                     
    body="""{                                                                                                           
        "resource_type": "LogicalRouterDownLinkPort",                                                                     
        "logical_router_id": "%s",                                                                                      
        "linked_logical_switch_port_id":{                                                                               
                "target_type": "LogicalPort",                                                                           
                "target_id": "%s"                                                                                       
                },                                                                                                        
         "subnets": [                                                                                                   
                {                                                                                                       
                 "ip_addresses": [                                                                                      
                        "%s"                                                                                            
                ],                                                                                                      
                 "prefix_length": "%s"                                                                                  
                }                                                                                                       
                ]                                                                                                       
        }"""%(lr0uuid,overlaylswport,ipaddr,length)                                                                 
    conn=requests.post(url,verify=False,headers=header,data=body)                                                       
    result=json.loads(conn.text).get('id')                                                                              
    if conn.status_code==201:                                                                                           
       uuid=json.loads(conn.text).get('id')                                                                             
       print "The logical router port "+str(uuid)+" has been created sucessfully"                                        
       return uuid                                                                                                      
    else:                                                                                                               
       print "the result code is "+str(conn.status_code)+" not sucessfully"                  
       quit()

### IP block section ### 
# create ip block 
# name: ip block name
# cidr: subnet with length eg: 192.168.0.0/24
def create_ipblock(name,cidr):
    ep="/api/v1/pools/ip-blocks"
    url="https://"+str(mgr)+str(ep)
    body="""{
    	"display_name": "%s",
  	"description": "",
  	"cidr": "%s",
  	"tags": [
  	{
  	"scope" : "%s",                                                     
  	"tag" : "%s"  
  	}
  	]
	}"""%(name,cidr,scope,tag)
    conn=requests.post(url,verify=False,headers=header,data=body)
    if conn.status_code==201:                                                                                                   
       uuid=json.loads(conn.text).get('id')                                                                                     
       print "The logical router port "+str(uuid)+" has been created sucessfully"                                               
       return uuid                                                                                                              
    else:                                                                                                                       
       print "the result code is "+str(conn.status_code)+" not sucessfully"                                       
       quit()
