"""
Use the Nutanix v4 API to update a Prism Central image
"""

import getpass
import argparse
import urllib3
import uuid
import sys

import ntnx_vmm_py_client
from ntnx_vmm_py_client import ApiClient as VMMClient
from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client.rest import ApiException as VMMException

"""
suppress warnings about insecure connections
consider the security implications before
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
    config = VMMConfiguration()
    config.host = pc_ip
    config.username = username
    config.password = cluster_password
    # known issue in pc.2022.6 that ignores this setting
    config.max_retry_attempts = 1
    config.backoff_factor = 3
    config.verify_ssl = False
    try:

        api_client = VMMClient(configuration=config)
        api_instance = ntnx_vmm_py_client.api.ImagesApi(api_client=api_client)
        # get a list of existing images
        images_list = api_instance.get_images_list()
        if images_list.metadata.total_available_results > 0:
            print(
                f"Images found: {len(images_list.data)}"
            )
        else:
            print("No images found.")
            sys.exit()

        # images have been found - update the first image in the list
        # to begin, we must retrieve that image's details
        existing_image = api_instance.get_image_by_ext_id(images_list.data[0].ext_id)

        # get the existing image's Etag
        existing_image_etag = existing_image.data._reserved["ETag"]

        # create a new Prism Central image instance
        new_image = ntnx_vmm_py_client.Ntnx.vmm.v4.images.Image.Image()
        new_image.data = existing_image.data
        new_image.name = f"{existing_image.data.name} - Updated"
        new_image.type = existing_image.data.type

        # add the existing image's Etag as a new request header
        api_client.add_default_header(header_name="If-Match", header_value=existing_image_etag)
        # create a new UUID to be used as the value of the Ntnx-Request-Id header
        request_id = str(uuid.uuid1())
        api_client.add_default_header(header_name="Ntnx-Request-Id", header_value=request_id)

        # update the image using a synchronous request (will wait until completion before returning)
        image_update = api_instance.update_image_by_ext_id(body=new_image, extId=existing_image.data.ext_id, async_req=False)
        print(image_update)

    except VMMException as e:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Please check your username and/or password, then try again.  \
Exception details: {e}"
        )
