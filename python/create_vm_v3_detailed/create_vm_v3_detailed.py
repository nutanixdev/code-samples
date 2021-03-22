'''
use the Prism REST API v3 to create a detailed VM
configures VM with most commonly-required fields
'''

import requests
import urllib3
import argparse
import getpass
import json
from base64 import b64encode
import sys
import os

'''
suppress warnings about insecure connections
you probably shouldn't do this in production
'''
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

'''
setup our command line parameters
for this example we only require the a single parameter - the name of the JSON file that contains our request parameters
this is a very clean way of passing parameters to this sort of script, without the need for excessive parameters on the command line
'''
parser = argparse.ArgumentParser()
parser.add_argument('json',
                    help='JSON file containing query parameters')
args = parser.parse_args()

'''
try and read the JSON parameters from the supplied file
'''
json_data = ''
try:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    with open(f'{script_dir}/{args.json}', 'r') as params:
        json_data = json.load(params)
except FileNotFoundError:
    print(f'{args.json} parameters file not found.')
    sys.exit()
except json.decoder.JSONDecodeError:
    print(f'{args.json} does not appear to contain valid JSON.  Please check the file and try again.')
    sys.exit()

# get the cluster password
cluster_password = getpass.getpass(prompt='Please enter your cluster password: ',stream=None)

try:

    '''
    setup the HTTP Basic Authorization header based on the supplied username and password
    done this way so that passwords are not supplied on the command line
    '''
    encoded_credentials = b64encode(bytes(f"{json_data['username']}:{cluster_password}",
                                    encoding="ascii")).decode("ascii")
    auth_header = f'Basic {encoded_credentials}'

    # setup the URL that will be used for the API request
    url = f"https://{json_data['cluster_ip']}:9440/api/nutanix/v3/vms"

    # setup the JSON payload that will be used for this request
    payload = f'{{ \
        "spec":{{ \
            "name":"{json_data["""vm_name"""]}", \
            "resources":{{ \
                "power_state":"ON", \
                "num_vcpus_per_socket":{json_data["""vcpus_per_socket"""]}, \
                "num_sockets":{json_data["""num_sockets"""]}, \
                "memory_size_mib":{json_data["""memory_size_mib"""]}, \
                "disk_list":[{{ \
                    "disk_size_mib":{json_data["""first_disk_size_mib"""]}, \
                    "device_properties":{{ \
                        "device_type":"DISK" \
                    }} \
                }}, \
                {{ \
                    "device_properties":{{ \
                        "device_type":"CDROM" \
                    }} \
                }}], \
                "nic_list":[{{ \
                    "nic_type":"NORMAL_NIC", \
                    "is_connected":true, \
                    "ip_endpoint_list":[{{ \
                        "ip_type":"DHCP" \
                    }}], \
                    "subnet_reference":{{ \
                        "kind":"subnet", \
                        "name":"{json_data["""first_nic_subnet_name"""]}", \
                        "uuid":"{json_data["""first_nic_subnet_uuid"""]}" \
                    }} \
                }}], \
                "guest_tools":{{ \
                    "nutanix_guest_tools":{{ \
                        "state":"ENABLED", \
                        "iso_mount_state":"MOUNTED" \
                    }} \
                }} \
            }}, \
            "cluster_reference":{{ \
                "kind":"cluster", \
                "name":"{json_data["""cluster_name"""]}", \
                "uuid":"{json_data["""cluster_uuid"""]}" \
            }} \
        }}, \
        "api_version":"3.1.0", \
        "metadata":{{ \
            "kind":"vm" \
        }} \
    }}'

    '''
    setup the request headers
    note the use of {auth_header} i.e. the Basic Authorization credentials we setup earlier
    '''
    headers = {
        'Accept': "application/json",
        'Content-Type': "application/json",
        'Authorization': f"{auth_header}",
        'cache-control': "no-cache"
        }

    # submit the request
    try:
        response = requests.request("POST", url, data=payload, headers=headers,
                                    verify=False,
                                    timeout=1)
        if(response.ok):
            print(response.text)
        else:
            print(f'An error occurred while connecting to {json_data["cluster_ip"]}.')
            # the following line can be uncommented to show detailed error information
            # print(response.text)
    except Exception as ex:
        print(f'An {type(ex).__name__} exception occurred while connecting to {json_data["cluster_ip"]}.\nArgument: {ex.args}.')

except KeyError:
    print(f'{args.json} file does not appear to contain the required fields.  Please check the file and try again.')

'''
wait for the enter key before continuing
this is to prevent terminal flashing if being run inside VS Code, for example
'''
input('Press ENTER to exit.')
