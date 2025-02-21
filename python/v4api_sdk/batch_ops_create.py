"""
Use the Nutanix v4 API SDKs to demonstrate Prism batch CREATE operations
Requires Prism Central 2024.1 or later and AOS 6.8 or later
"""

import getpass
import argparse
import sys
import uuid
from pprint import pprint
import urllib3

import ntnx_vmm_py_client
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

from tme.utils import Utils


def main():
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
    parser.add_argument(
        "-p", "--poll", help="Time between task polling, in seconds", default=1
    )
    args = parser.parse_args()

    # get the cluster password
    cluster_password = getpass.getpass(
        prompt="Enter your Prism Central \
password: ",
        stream=None,
    )

    pc_ip = args.pc_ip
    username = args.username
    poll_timeout = args.poll

    # make sure the user enters a password
    if not cluster_password:
        while not cluster_password:
            print(
                "Password cannot be empty.  \
    Enter a password or Ctrl-C/Ctrl-D to exit."
            )
            cluster_password = getpass.getpass(
                prompt="Enter your Prism Central password: ", stream=None
            )

    try:
        # create utils instance for re-use later
        utils = Utils(pc_ip=pc_ip, username=username, password=cluster_password)

        cluster_config = ClusterConfiguration()
        prism_config = PrismConfiguration()
        for config in [cluster_config, prism_config]:
            # create the configuration instances
            config.host = pc_ip
            config.username = username
            config.password = cluster_password
            config.verify_ssl = False

        # before submitting the batch we need to find out which cluster
        # the VMs will live on
        # for this demo, we will get the ext_id of the first non-PC
        # cluster visible in this PC instance
        cluster_client = ClusterClient(configuration=cluster_config)
        cluster_instance = ntnx_clustermgmt_py_client.api.ClustersApi(
            api_client=cluster_client
        )
        print("Retrieving cluster list ...")
        cluster_list = cluster_instance.list_clusters(async_req=False)

        # do some verification and make sure the user creates the image on the correct cluster
        found_clusters = []

        for cluster in cluster_list.data:
            if not cluster.name == "Unnamed":
                found_clusters.append({"name": cluster.name, "ext_id": cluster.ext_id})
        print(
            f"The following clusters ({len(cluster_list.data)-1}) were found, not including Prism Central."
        )
        print(
            "Note: By default Prism Central clusters appear as 'Unnamed'.  Clusters matching this name have \
not been included in this list."
        )
        pprint(found_clusters)
        expected_cluster_name = input(
            "\nEnter the name of the destination cluster: "
        ).lower()

        matches = [
            x
            for x in found_clusters
            if x["name"].lower() == expected_cluster_name.lower()
        ]
        if not matches:
            print(
                f"No cluster found matching the name {expected_cluster_name}.  Exiting."
            )
            sys.exit()

        # get the cluster ext_id
        cluster_ext_id = matches[0]["ext_id"]

        # setup the configuration parameters
        prism_config.host = pc_ip
        prism_config.username = username
        prism_config.password = cluster_password
        prism_config.verify_ssl = False
        prism_client = PrismClient(configuration=prism_config)
        prism_client.add_default_header(
            header_name="Accept-Encoding", header_value="gzip, deflate, br"
        )
        batch_instance = ntnx_prism_py_client.api.BatchesApi(api_client=prism_client)

        # generate unique ID to ensure image names are always different
        unique_id = uuid.uuid1()

        batch_count = input(
            "\nEnter the number of virtual machines you would like to create: "
        ).lower()

        confirm_create = utils.confirm("Submit batch operation?")
        if confirm_create:
            # initiate the list of VMs that will be created
            # this is a list of BatchSpecPayload
            batch_spec_payload_list = []
            prefix = "batchdemo"
            for i in range(int(batch_count)):
                vm_name = f"{prefix}{i}_{unique_id}"
                description = f"{prefix}"
                memory_size_mib = 1024
                vm_payload = {
                    "name": vm_name,
                    "description": f"{description}_{unique_id}",
                    "memory_size_bytes": memory_size_mib * 1024 * 1024,
                    "cluster": ntnx_vmm_py_client.AhvConfigClusterReference(
                        ext_id=cluster_ext_id
                    ),
                }
                batch_spec_payload_list.append(BatchSpecPayload(data=vm_payload))

            batch_spec = BatchSpec(
                metadata=BatchSpecMetadata(
                    action=ActionType.CREATE,
                    name=f"multi_{unique_id}",
                    uri="/api/vmm/v4.0.b1/ahv/config/vms",
                    stop_on_error=True,
                    chunk_size=1,
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
                pc_ip=pc_ip,
                username=username,
                password=cluster_password,
                poll_timeout=poll_timeout,
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
