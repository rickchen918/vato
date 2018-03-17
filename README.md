# vato2 project 
The project is to create for provision simplification upon nsx-t and k8s
The project includes 2 main parts 

1) NSX provisioing 
	- Using ansibe to provision basic nsx installation 
		. Deploy nsx ova
		. Register and build nsx controller cluster 
		. Register and build nsx edge node and edge cluster 
	- Configure basic nsx configuration by python script (under nsx folder)
		. Create transport zone for vlan
		. Create transport zone for overlay with tag (required for k8s integration) 
		. Create uplink profile for edge transport node 
		. Create ip pool for TEP ( here is hard-code in script ). if you want to changes subnet, 
		  it can be on section of "create ip tool for transport node"
		. Create ip pool fo nat with tag ( requried for k8s integration ) 
		. Create logical switch for k8s management and overlay
		. Create Tier0 router with tags ( required for k8s integration ) 
		. Connect Tier0 to logical switch 
		. Create IP Block with tag ( required for k8s integration ) 

2) K8s cluster provisioing 
	- Deployment container host VM by ansible ( The built-in container VM )  
	- Scan logical switch to get connected vif of containe-host-vm and update tag ( required for k8s integration )
	- Install required packages for K8s and NSX-T container packages  
	- Init K8s Cluster 
	- Configure NSX NCP plugin for K8s 

The project is on early stage for demo purpose, to fit various envionment, you may need to know the file placement to modify for deployment fitting. 

	- vato folder 
		. answer.yml : most provision variable is written here ( vc, nsx and k8s ) , it could be too much info 
		  required, but we will improve as possible latera
		. host.yml : the definition of ansible target 

	- nsx folder
		. nsxt_go.yml : provisning flow of nsx deployment 
		. roles : the provision execution steps of flow 
		. python folder: nsx logical configuration script 
		. package folder: nsx ova file placement 

	- k8s folder
		. k8s_go.yml : provisning flow of k8s deployment
		. roles : the provision execution steps of flow
		. python folder: nsx logical port tagging script for nsx ncp 
		. package folder: k8s container-vm ova and nsx-t container package
		. template folder: plugin template for ncp and node 

How to use vato:
	- if you setup environement properly 
	- run command under nsx folder to provision 
		example: ~/vato/nsx$ ansible-playbook -i ../host.yml nsxt_go.yml
        - manual configuration nsx environment
		. Due the demo environment difference, we leave little configuration for manual provisoing
		. user needs to create its own vlan logical switch , tier 1 uplink port 
		. user needs to create its own default route and route distribution 
		. make sure that vato appliance is able to reach conatiner-vm  
	- run command under k8s folder to provision 
		example: ~/vato/k8s$ ansible-playbook -i ../host.yml k8s_go.ym
