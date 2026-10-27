"""
Use the Nutanix v4 REST APIs to update a Prism Central image
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import requests
import urllib3
import getpass
import argparse
import uuid
import json
import sys
from base64 import b64encode
import rich

"""
suppress warnings about insecure connections
please consider the security implications before doing this in a production environment
"""
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

"""
setup the command line parameters
for this example only two parameters are required
- the Prism Central IP address or FQDN
- the Prism Central username; the script will prompt for the user's password
  so that it never needs to be stored in plain text
"""
parser = argparse.ArgumentParser()
parser.add_argument("pc_ip", help="Prism Central IP address or FQDN")
parser.add_argument("username", help="Prism Central username")
args = parser.parse_args()

# get the cluster password
cluster_password = getpass.getpass(
    prompt="Please enter your Prism Central \
password: ",
    stream=None,
)

pc_ip = args.pc_ip
username = args.username

# at current release, the latest Nutanix v4 REST API version is 4.2
api_version = "v4.2"

# make sure the user enters a password
if not cluster_password:
    while not cluster_password:
        print(
            "Password cannot be empty. Please enter a password or Ctrl-C/Ctrl-D to exit."
        )
        cluster_password = getpass.getpass(
            prompt="Please enter your Prism Central password: ", stream=None
        )

try:

    """
    setup the HTTP Basic Authorization header based on the
    supplied username and password
    """
    encoded_credentials = b64encode(
        bytes(f"{username}:{cluster_password}", encoding="ascii")
    ).decode("ascii")
    auth_header = f"Basic {encoded_credentials}"
    # setup the URL that will be used for the API request
    url = f"https://{pc_ip}:9440/api/vmm/{api_version}/content/images"

    """
    setup the request headers
    note the use of {auth_header} i.e. the Basic Authorization
    credentials we setup earlier
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"{auth_header}",
        "cache-control": "no-cache",
    }
    # submit the request
    try:
        response = requests.request(
            "GET", url, headers=headers, verify=False, timeout=10
        )
        if response.ok:
            # show a total count of images found
            print(
                f'Total images found: {response.json()["metadata"]["totalAvailableResults"]}'
            )
        else:
            print(f"An error occurred while connecting to {pc_ip}.")
            """
            the following line can be uncommented to show
            detailed error information
            """
            print(response.text)
            sys.exit()

        # images have been found - update the first image in the list
        # to begin, we must retrieve that image's details
        existing_image_ext_id = response.json()["data"][0]["extId"]
        # get the existing image details
        url = f"https://{pc_ip}:9440/api/vmm/{api_version}/content/images/{existing_image_ext_id}"
        existing_image = requests.get(url, headers=headers, verify=False, timeout=10)

        # get the existing image's resource Etag
        existing_image_etag = existing_image.headers["Etag"]

        # show image details before continuing
        print(f"\nImage name: {existing_image.json()['data']['name']}")
        print(f"This image will be renamed to \"{existing_image.json()['data']['name']} - Updated\"\n")

        # create a new UUID to be used as the value of the Ntnx-Request-Id header
        request_id = str(uuid.uuid1())

        # create new headers that include the existing image's resource Etag and Ntnx-Request-Id
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"{auth_header}",
            "cache-control": "no-cache",
            "If-Match": existing_image_etag,
            "Ntnx-Request-Id": request_id,
        }

        # create the image update's JSON request payload
        update_payload = existing_image.json()["data"]

        # alter the image's name
        update_payload["name"] = f'{update_payload["name"]} - Updated'

        # update the image
        url = f"https://{pc_ip}:9440/api/vmm/{api_version}/content/images/{existing_image_ext_id}"
        update = requests.put(url, headers=headers, data=json.dumps(update_payload), verify=False, timeout=10)
        
        errors = [ flag for flag in update.json()['metadata']['flags'] if flag['name'].lower() == 'haserror' and flag['value'] == True]

        if errors:
            print("An error occurred while updating the image.  Full response:")
            print(update.json() + "\n")
        else:
            print("Image update successful.\n")

    except Exception as ex:
        print(
            f"An {type(ex).__name__} exception occurred while \
              connecting to {pc_ip}.\nArgument: {ex.args}."
        )

# catching all exceptions like this should be generally be avoided
except Exception as e:
    print(f"{e}")
