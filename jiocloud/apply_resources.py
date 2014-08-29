#!/usr/bin/env python
import yaml
import os
import keystoneclient.v2_0.client as ksclient
import time
from novaclient import client as novaclient

"""
Parses a specification of nodes to install and makes it so
"""

def get_nova_creds_from_env():
    d = {}
    d['username'] = os.environ['OS_USERNAME']
    d['api_key'] = os.environ['OS_PASSWORD']
    d['auth_url'] = os.environ['OS_AUTH_URL']
    d['project_id'] = os.environ['OS_TENANT_NAME']
    return d

def get_nova_client():
    return novaclient.Client("1.1", **get_nova_creds_from_env())

def get_resource_file_path(path, env):
    return os.path.join(path, env + ".yaml")

def read_resources(path):
    fp = file(path)
    return yaml.load(fp)['resources']

def get_existing_servers(nova_client, project_tag=None):
    """
    This method accepts an option project tag
    """
    servers = nova_client.servers.list()
    if project_tag:
        servers = [elem.name for elem in servers if elem.name.endswith('_' + project_tag) ]
    return servers

def generate_desired_servers(resources, project_tag=None):
    """
    Convert from a hash of servers resources to the
    hash of all server names that should be created
    """
    suffix = (project_tag and ('_' + project_tag)) or ''

    servers_to_create = []
    for k,v in resources.iteritems():
        for i in range(int(v['number'])):
            # NOTE ideally, this would not contain the caridinatlity
            # b/c it is not needed by this hash
            server = {'name': "%s%d%s"%(k, i+1, suffix)}
            servers_to_create.append(dict(server.items() + v.items()))
    return servers_to_create

def servers_to_create(nova_client, resource_file, project_tag=None):
    resources = read_resources(resource_file)
    existing_servers     = get_existing_servers(nova_client, project_tag=project_tag)
    desired_servers      = generate_desired_servers(resources, project_tag)
    return [elem for elem in desired_servers if elem['name'] not in existing_servers ]

def create_servers(nova_client, servers):
    for s in servers:
        create_server(nova_client, **s)

images={}
flavors={}
def create_server(nova_client, name, flavor, image, networks, **keys):
    print "Creating server %s"%(name)
    images[image]   = images.get(image, nova_client.images.find(name=image))
    flavors[flavor] = flavors.get(flavor, nova_client.flavors.find(name=flavor))
    net_list=[]
    for n in networks:
      net_list.append({'net-id': n})
    instance = nova_client.servers.create(
      name=name,
      image=images[image],
      flavor=flavors[flavor],
      nics=net_list,
    )

    # Poll at 5 second intervals, until the status is no longer 'BUILD'
    status = instance.status
    while status == 'BUILD':
        time.sleep(5)
        # Retrieve the instance again so the status field updates
        instance = nova_client.servers.get(instance.id)
        status = instance.status
        print "status: %s" % status

# main
#path = get_resource_file_path(os.getcwd() + "/environment_resources", 'prod')
#nova_client = get_nova_client()
#servers = servers_to_create(get_nova_client(), path, project_tag='dan123')
#create_servers(nova_client, servers)
