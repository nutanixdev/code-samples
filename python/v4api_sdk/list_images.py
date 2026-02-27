"""
Use the Nutanix v4 API SDKs to request and parse a list of all available images
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import getpass
import argparse
import urllib3
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

        # without filters
        print("Building image list without filters ...")
        images_list_no_filters = vmm_instance.list_images(async_req=False)
        if images_list_no_filters.metadata.total_available_results > 0:
            print(
                f"Images found without any filters: {len(images_list_no_filters.data)}"
            )
        else:
            print("No images found.")

        # with filters
        print("Building image list filtered by image names starting with \"A\" ...")
        images_list_with_filter = vmm_instance.list_images(
            async_req=False,
            _filter="startswith(name, 'A')"
        )
        if images_list_with_filter.metadata.total_available_results > 0:
            print(
                f"Images with name beginning with 'A': {len(images_list_with_filter.data)}"
            )
        else:
            print('No images found with name starting with "A".')

        print("Building image list filtered by images named \"scenario01\" ...")
        images_list_matches = vmm_instance.list_images(
            async_req=False,
            _filter="name in ('scenario01')"
        )
        if images_list_matches.metadata.total_available_results > 0:
            print(f"Images found with names in list: {len(images_list_matches.data)}")
        else:
            print("No images found matching this filter.")

        # order by name
        print("\nBuilding image list, all images ordered by name (ascending) ...")
        images_list_orderby_name = vmm_instance.list_images(
            async_req=False,
            _orderby="name asc"
        )
        if images_list_orderby_name.metadata.total_available_results > 0:
            print("\nImages found in PC instance, ordered by name, ascending:")
            for image in images_list_orderby_name.data:
                print(f"Image name: {image.name} ({image.ext_id})")
        else:
            print("No images found while using order by name filter.")

        # order by size
        print("\nBuilding image list, all images ordered by size (descending) ...")
        images_list_orderby_size = vmm_instance.list_images(
            async_req=False,
            _orderby="sizeBytes desc"
        )
        if images_list_orderby_size.metadata.total_available_results > 0:
            print("\nImages found in PC instance, ordered by size, descending:")
            for image in images_list_orderby_size.data:
                print(f"Image name: {image.name}, size (bytes): {image.size_bytes}")
        else:
            print("No images found while using order by size filter.")
    except VMMException as e:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Please check your username and/or password, then try again.  \
Exception details: {e}"
        )

if __name__ == "__main__":
    main()
