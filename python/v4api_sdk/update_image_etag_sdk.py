"""
Use the Nutanix v4 Python SDK to update a Prism Central image

Requires Prism Central 2024.1 or later and AOS 6.8 or later
"""

import getpass
import argparse
import urllib3
import sys

import ntnx_vmm_py_client
from ntnx_vmm_py_client import ApiClient as VMMClient
from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client.rest import ApiException as VMMException

from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client import Configuration as PrismConfiguration

from tme.utils import Utils

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

# create utils instance for re-use later
utils = Utils(pc_ip=pc_ip, username=username, password=cluster_password)

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
    vmm_config = VMMConfiguration()
    prism_config = PrismConfiguration()

    for config in [vmm_config, prism_config]:
        config.host = pc_ip
        config.username = username
        config.password = cluster_password
        config.verify_ssl = False

    try:
        vmm_client = VMMClient(configuration=vmm_config)
        prism_client = PrismClient(configuration=prism_config)

        for client in [vmm_client, prism_client]:
            client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )

        vmm_instance = ntnx_vmm_py_client.api.ImagesApi(api_client=vmm_client)
        # get a list of existing images
        images_list = vmm_instance.list_images()
        if images_list.metadata.total_available_results > 0:
            print(f"Images found: {len(images_list.data)}")
        else:
            print("No images found.")
            sys.exit()

        # images have been found - update the first image in the list
        # to begin, we must retrieve that image's details
        print("Getting image ...")
        existing_image = vmm_instance.get_image_by_id(images_list.data[0].ext_id)

        # get the existing image's Etag
        # existing_image_etag = existing_image.data._reserved["ETag"]
        existing_image_etag = vmm_client.get_etag(existing_image)

        print(f"Working with image named {existing_image.data.name} ...")

        # create a new Prism Central image instance
        new_image = ntnx_vmm_py_client.models.vmm.v4.content.Image.Image()
        new_image.data = existing_image.data
        new_image.name = f"{existing_image.data.name} - Updated"
        new_image.type = existing_image.data.type

        # add the existing image's Etag as a new request header
        vmm_client.add_default_header(
            header_name="If-Match", header_value=existing_image_etag
        )

        # update the image using a synchronous request (will wait until completion before returning)
        image_update = vmm_instance.update_image_by_id(
            body=new_image, extId=existing_image.data.ext_id, async_req=False
        )
        task_extid = image_update.data.ext_id
        utils.monitor_task(
            task_ext_id=task_extid,
            task_name="Update image",
            pc_ip=pc_ip,
            username=username,
            password=cluster_password,
            poll_timeout=1,
            prefix="",
        )

    except VMMException as e:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Please check your username and/or password, then try again.  \
Exception details: {e}"
        )
