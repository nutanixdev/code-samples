"""
Use the Nutanix v4 REST APIs to request and parse a list of all available images
"""

import requests
import urllib3
import getpass
import argparse
from base64 import b64encode

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
    url = f"https://{pc_ip}:9440/api/vmm/v4.0.b1/content/images"

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
                f'Total images found: {response.json()["metadata"]["totalAvailableResults"]}:'
            )
            for image in response.json()["data"]:
                print(f'- {image["name"]}')
        else:
            print(f"An error occurred while connecting to {pc_ip}.")
            """
            the following line can be uncommented to show
            detailed error information
            """
            print(response.text)
    except Exception as ex:
        print(
            f"An {type(ex).__name__} exception occurred while \
              connecting to {pc_ip}.\nArgument: {ex.args}."
        )

# catching all exceptions like this should be generally be avoided
except Exception as e:
    print(f"{e}")
