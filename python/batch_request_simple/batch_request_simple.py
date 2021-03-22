'''
use the Prism REST API v3 to combine multiple requests
into a single batch via POST
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
for this example we only require the a single parameter
- the name of the JSON file that contains our request parameters
this is a very clean way of passing parameters to this sort of
script, without the need for excessive parameters on the command line
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
    print(f'{args.json} does not appear to contain valid JSON.  \
          Please check the file and try again.')
    sys.exit()

# get the cluster password
cluster_password = getpass.getpass(prompt='Please enter your cluster \
password: ', stream=None)

try:

    '''
    setup the HTTP Basic Authorization header based on the
    supplied username and password
    done this way so that passwords are not supplied on the command line
    '''
    encoded_credentials = b64encode(bytes(
                                    f'{json_data["username"]}:{cluster_password}',
                                    encoding='ascii')).decode('ascii')
    auth_header = f'Basic {encoded_credentials}'

    # setup the URL that will be used for the API request
    url = f'https://{json_data["cluster_ip"]}:9440/api/nutanix/v3/batch'

    # setup the JSON payload that will be used for this request
    payload = json.dumps(json_data['batch_details'])

    '''
    setup the request headers
    note the use of {auth_header} i.e. the Basic Authorization
    credentials we setup earlier
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
                                    verify=False)

        if(response.ok):
            print(response.text)
        else:
            print(f'An error occurred while connecting to {json_data["cluster_ip"]}.')
            '''
            the following line can be uncommented to show
            detailed error information
            '''
            print(response.text)
    except Exception as ex:
        print(f'An {type(ex).__name__} exception occurred while \
              connecting to {json_data["cluster_ip"]}.\nArgument: {ex.args}.')

except KeyError:
    print(f'{args.json} file does not appear to contain the required \
          fields.  Please check the file and try again.')

'''
wait for the enter key before continuing
this is to prevent terminal flashing if being run inside VS Code, for example
'''
input('Press ENTER to exit.')
