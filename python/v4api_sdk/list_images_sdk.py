"""
Use the Nutanix v4 API SDKs to request and parse a list of all available images
"""

import getpass
import argparse
import urllib3
import sys
# from pprint import pprint

import ntnx_vmm_py_client
from ntnx_vmm_py_client import ApiClient
from ntnx_vmm_py_client import Configuration
from ntnx_vmm_py_client.rest import ApiException

"""
suppress warnings about insecure connections
please consider the security implications before
doing this in a production environment
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
            "Password cannot be empty.  \
Please enter a password or Ctrl-C/Ctrl-D to exit."
        )
        cluster_password = getpass.getpass(
            prompt="Please enter your Prism Central password: ", stream=None
        )

if __name__ == "__main__":
    config = Configuration()
    config.host = pc_ip
    config.username = username
    config.password = cluster_password
    # known issue in pc.2022.6 that ignores this setting
    config.max_retry_attempts = 1
    config.backoff_factor = 3
    config.verify_ssl = False
    try:

        api_client = ApiClient(configuration=config)
        api_instance = ntnx_vmm_py_client.api.ImagesApi(api_client=api_client)
        # without filters
        images_list_no_filters = api_instance.get_images_list()
        print(f"Images found without any filters: {len(images_list_no_filters.data)}")
        # with filters
        images_list_with_filter = api_instance.get_images_list(_filter="startswith(name, 'U')")
        print(f"Images with name beginning with 'U': {len(images_list_with_filter.data)}")
        images_list_matches = api_instance.get_images_list(_filter="name in ('FSC 1.1.0','prod','staging')")
        print(f"Images found with names in list: {len(images_list_matches.data)}")
        # using _orderby
        images_list_orderby_name = api_instance.get_images_list(_orderby="name asc")
        print(f"\nImages found in PC instance, ordered by name, ascending:")
        for image in images_list_orderby_name.data:
            print(f"Image name: {image.name}")
        images_list_orderby_size = api_instance.get_images_list(_orderby="sizeBytes desc")
        print(f"\nImages found in PC instance, ordered by size, ascending:")
        for image in images_list_orderby_size.data:
            print(f"Image name: {image.name}, size (bytes): {image.size_bytes}")
    except ApiException as e:
        print(f"Unable to authenticate using the supplied credentials.  \
Please check your username and/or password, then try again.  \
Exception details: {e}")
