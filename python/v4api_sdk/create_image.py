"""
Use the Nutanix v4 API SDKs to create a Prism Central image
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import getpass
import argparse
import sys
import uuid
from pprint import pprint
import urllib3
from rich import print

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VmmConfiguration
from ntnx_vmm_py_client import ApiClient as VmmClient
from ntnx_vmm_py_client.rest import ApiException as VMMException

import ntnx_clustermgmt_py_client
from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient


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
        cluster_config = ClusterConfiguration()

        for config in [vmm_config, cluster_config]:
            config.host = script_config.pc_ip
            config.port = "9440"
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False

        # create the instance of the ApiClient class
        vmm_client  = VmmClient(configuration=vmm_config)
        cluster_client = ClusterClient(configuration=cluster_config)

        # create the API class instances
        vmm_instance = ntnx_vmm_py_client.api.ImagesApi(api_client=vmm_client)
        cluster_instance = ntnx_clustermgmt_py_client.api.ClustersApi(api_client=cluster_client)

        # use an Odata filter to retrieve a list of clusters, filtered by AOS clusters ONLY
        # in the context of this query, the valid cluster function values are 'AOS' and 'PRISM_CENTRAL'
        print("Retrieving cluster list ...")
        cluster_list = cluster_instance.list_clusters(
            async_req=False,
            _filter="config/clusterFunction/any(a:a eq Clustermgmt.Config.ClusterFunctionRef'AOS')"
        )

        # do some verification and make sure the user creates the image on the correct cluster
        found_clusters = []

        for cluster in cluster_list.data:
            found_clusters.append({"name": cluster.name, "ext_id": cluster.ext_id})
        print(
            f"({len(cluster_list.data)}) AOS clusters were found; this does not include Prism Central clusters."
            )
        pprint(found_clusters)
        expected_cluster_name = input(
                "\nPlease enter the name of the destination cluster: "
                ).lower()

        matches = [
                cluster
                for cluster in found_clusters
                if cluster["name"].lower() == expected_cluster_name.lower()
                ]
        if not matches:
            print(
                    f"No cluster found matching the name {expected_cluster_name}.  Exiting."
                    )
            sys.exit()

        # get the cluster ext_id
        cluster_ext_id = matches[0]["ext_id"]

        vmm_client.add_default_header(
            header_name="Accept-Encoding",
            header_value="gzip, deflate, br"
        )

        # generate unique ID to ensure image names are always different
        unique_id = uuid.uuid1()

        # setup new image properties
        new_image = ntnx_vmm_py_client.models.vmm.v4.content.Image.Image()
        new_image.name = f"rocky_linux_10_cloud_{unique_id}"
        new_image.desc = "Rocky Linux 10 Cloud Image"
        new_image.type = "DISK_IMAGE"
        image_source = ntnx_vmm_py_client.models.vmm.v4.content.UrlSource.UrlSource()
        image_source.url = "https://dl.rockylinux.org/pub/rocky/10/images/x86_64/Rocky-10-GenericCloud-Base.latest.x86_64.qcow2" 
        image_source.allow_insecure = False
        new_image.source = image_source
        image_cluster = ntnx_vmm_py_client.models.vmm.v4.ahv.config.ClusterReference.ClusterReference()
        image_cluster.ext_id = cluster_ext_id
        new_image.initial_cluster_locations = [image_cluster]

        confirm_create = utils.confirm("Create image?")
        if confirm_create:
            print(f"Creating image with name {new_image.name} ...")
            image_create = vmm_instance.create_image(
                async_req=False,
                body=new_image
            )

            # grab the ext ID of the create image task
            # this method is a little cumbersome but allows task IDs from
            # different endpoints and APIs to be used with the
            # monitor_task function
            create_ext_id = image_create.data.ext_id
            utils.monitor_task(
                    task_ext_id=create_ext_id,
                    task_name="Create image",
                    pc_ip=script_config.pc_ip,
                    username=script_config.pc_username,
                    password=script_config.pc_password,
                    )
            print("Image created.")
        else:
            print("Image creation cancelled.")

    except VMMException as vmm_exception:
        print(
                f"Unable to authenticate using the supplied credentials.  \
                        Please check your username and/or password, then try again.  \
                        Exception details: {vmm_exception}"
                        )


if __name__ == "__main__":
    main()
