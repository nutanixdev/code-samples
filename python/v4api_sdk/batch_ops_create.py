"""
Use the Nutanix v4 API SDKs to demonstrate Prism batch CREATE operations
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

import ntnx_prism_py_client
from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient

import ntnx_clustermgmt_py_client
from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient

from ntnx_prism_py_client.models.prism.v4.operations.BatchSpec import BatchSpec
from ntnx_prism_py_client.models.prism.v4.operations.BatchSpecMetadata import (
    BatchSpecMetadata,
)
from ntnx_prism_py_client.models.prism.v4.operations.BatchSpecPayload import (
    BatchSpecPayload,
)

from ntnx_prism_py_client.models.prism.v4.operations.ActionType import ActionType

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
        cluster_config = ClusterConfiguration()
        prism_config = PrismConfiguration()

        for config in [cluster_config, prism_config]:
            config.host = script_config.pc_ip
            config.port = "9440"
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False

        # create the instance of the ApiClient class
        cluster_client  = ClusterClient(configuration=cluster_config)
        prism_client = PrismClient(configuration=prism_config)

        for client in [cluster_client, prism_client]:
            client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )

        # create the API class instances
        cluster_instance = ntnx_clustermgmt_py_client.api.ClustersApi(api_client=cluster_client)
        prism_instance = ntnx_prism_py_client.api.CategoriesApi(api_client=prism_client)
        batch_instance = ntnx_prism_py_client.api.BatchesApi(api_client=prism_client)

        # before submitting the batch we need to find out which cluster
        # the VMs will live on
        # for this demo, we will get the ext_id of the first non-PC
        # cluster visible in this PC instance
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
            "\nEnter the name of the destination cluster: "
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

        # generate unique ID to ensure image names are always different
        unique_id = uuid.uuid1()

        batch_count = input(
            "\nEnter the number of virtual machines you would like to create: "
        ).lower()

        confirm_create = utils.confirm("Submit batch operation?")
        if confirm_create:
            # initialize the list of VMs that will be created
            # this is a list of BatchSpecPayload
            batch_spec_payload_list = []
            prefix = "batchdemo"
            for i in range(int(batch_count)):
                vm_name = f"{prefix}{i}_{unique_id}"
                description = f"{prefix}"
                memory_size_mib = 1024
                vm_payload = ntnx_vmm_py_client.models.vmm.v4.ahv.config.Vm.Vm(
                    name=vm_name,
                    description=f"{description}_{unique_id}",
                    memory_size_bytes=memory_size_mib * 1024 * 1024,
                    cluster=ntnx_vmm_py_client.models.vmm.v4.ahv.config.ClusterReference.ClusterReference(
                        ext_id=cluster_ext_id
                    ),
                )
                batch_spec_payload_list.append(
                    BatchSpecPayload(
                        data=vm_payload,
                    )
                )

            batch_spec = BatchSpec(
                metadata=BatchSpecMetadata(
                    action=ActionType.CREATE,
                    name=f"multi_{unique_id}",
                    uri="/api/vmm/v4.2/ahv/config/vms",
                    stop_on_error=True,
                    chunk_size=20,
                ),
                payload=batch_spec_payload_list,
            )

            print(f"Submitting batch operation to create {batch_count} VMs ...")
            batch_response = batch_instance.submit_batch(
                async_req=False, body=batch_spec
            )

            # grab the ext ID of the batch operation task
            batch_ext_id = batch_response.data.ext_id
            utils.monitor_task(
                task_ext_id=batch_ext_id,
                task_name="Batch VM creation",
                pc_ip=script_config.pc_ip,
                username=script_config.pc_username,
                password=script_config.pc_password,
            )
            print("Batch operation completed.")
        else:
            print("Batch operation cancelled.")

    except VMMException as vmm_exception:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Check your username and/or password, then try again.  \
Exception details: {vmm_exception}"
        )


if __name__ == "__main__":
    main()
