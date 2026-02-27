"""
Use the Nutanix v4 Python SDK to update a Prism Central image
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import getpass
import argparse
import urllib3
import sys
from rich import print

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VmmConfiguration
from ntnx_vmm_py_client import ApiClient as VmmClient
from ntnx_vmm_py_client.rest import ApiException as VMMException

# small library that manages commonly-used tasks across these code samples
from tme.utils import Utils
from tme.apiclient import ApiClient


def main():
    
    """
    suppress warnings about insecure connections
    please consider the security implications before
    doing this in a production environment
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    utils = Utils()
    script_config = utils.get_environment()

    try:

        # create the configuration instance
        # this per-namespace class manages all Prism Central connection settings
        vmm_config = VmmConfiguration()

        for config in [vmm_config]:
            config.host = script_config.pc_ip
            config.port = "9440"
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False

        # create the instance of the ApiClient class
        vmm_client  = VmmClient(configuration=vmm_config)

        # create the API class instances
        vmm_instance = ntnx_vmm_py_client.api.ImagesApi(api_client=vmm_client)

        # get a list of existing images
        images_list = vmm_instance.list_images(
            async_req=False
        )
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
        existing_image_etag = vmm_client.get_etag(existing_image)

        print(f"Working with image named {existing_image.data.name} ...")
        print(f"This image will be renamed to \"{existing_image.data.name} - Updated\"")

        # create a new Prism Central image instance
        new_image = ntnx_vmm_py_client.models.vmm.v4.content.Image.Image()
        new_image.data = existing_image.data
        new_image.name = f"{existing_image.data.name} - Updated"
        new_image.type = existing_image.data.type

        # add the existing image's Etag as a new request header
        vmm_client.add_default_header(
            header_name="If-Match",
            header_value=existing_image_etag
        )

        # update the image using a synchronous request (will wait until completion before returning)
        image_update = vmm_instance.update_image_by_id(
            body=new_image, extId=existing_image.data.ext_id, async_req=False
        )
        task_extid = image_update.data.ext_id
        utils.monitor_task(
            task_ext_id=task_extid,
            task_name="Update image",
            pc_ip=script_config.pc_ip,
            username=script_config.pc_username,
            password=script_config.pc_password,
            prefix="",
        )

    except VMMException as e:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Please check your username and/or password, then try again.  \
Exception details: {e}"
        )

if __name__ == "__main__":
    main()