"""
Use the Nutanix v4 API SDKs to demonstrate Prism batch MODIFY operations
Requires Prism Central 2024.1 or later and AOS 6.8 or later
"""

import getpass
import argparse
import sys
import uuid
import urllib3

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client import ApiClient as VMMClient
from ntnx_vmm_py_client.rest import ApiException as VMMException

import ntnx_prism_py_client
from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient

from ntnx_prism_py_client.models.prism.v4.operations.BatchSpec import BatchSpec
from ntnx_prism_py_client.models.prism.v4.operations.BatchSpecMetadata import (
    BatchSpecMetadata,
)
from ntnx_prism_py_client.models.prism.v4.operations.BatchSpecPayload import (
    BatchSpecPayload,
)
from ntnx_prism_py_client.models.prism.v4.operations.BatchSpecPayloadMetadata import (
    BatchSpecPayloadMetadata,
)
from ntnx_prism_py_client.models.prism.v4.operations.BatchSpecPayloadMetadataHeader import (
    BatchSpecPayloadMetadataHeader,
)

from ntnx_prism_py_client.models.prism.v4.operations.BatchSpecPayloadMetadataPath import (
    BatchSpecPayloadMetadataPath,
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

        prism_config = PrismConfiguration()
        vmm_config = VMMConfiguration()
        for config in [prism_config, vmm_config]:
            # create the configuration instances
            config.host = pc_ip
            config.username = username
            config.password = cluster_password
            config.verify_ssl = False

        # get an existing VM
        # for demo purposes we're filering specific VMs; for your environment
        # you will need to change this filter to suit your needs or specify
        # an exact VM ext_id
        vmm_client = VMMClient(configuration=vmm_config)
        vmm_instance = ntnx_vmm_py_client.api.VmApi(api_client=vmm_client)
        print("Building filtered list of existing VMs ...")
        print("Note: By default this will retrieve a maximum of 50 VMs.")
        vm_list = vmm_instance.list_vms(
            async_req=False, _filter="startswith(name, 'batchdemo')"
        )
        if vm_list.data:
            print(f"{len(vm_list.data)} VM(s) found:")
            for vm in vm_list.data:
                print(f"- {vm.name}")
        else:
            print("No matching VMs found.  Exiting ...")
            sys.exit()

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

        confirm_create = utils.confirm("Submit batch operation?")
        if confirm_create:
            # initiate the list of VMs that will be created
            # this is a list of BatchSpecPayload
            batch_spec_payload_list = []

            print("Building VM batch modify payload ...")
            for vm in vm_list.data:
                existing_vm = vmm_instance.get_vm_by_id(vm.ext_id)
                existing_vm.data.name = f"MODIFIED_{existing_vm.data.name}"
                etag = vmm_client.get_etag(existing_vm)
                batch_spec_payload_list.append(
                    BatchSpecPayload(
                        data=existing_vm.data,
                        metadata=BatchSpecPayloadMetadata(
                            headers=[
                                BatchSpecPayloadMetadataHeader(
                                    name="If-Match", value=etag
                                )
                            ],
                            path=[
                                BatchSpecPayloadMetadataPath(
                                    name="extId", value=existing_vm.data.ext_id
                                )
                            ],
                        ),
                    )
                )

            batch_spec = BatchSpec(
                metadata=BatchSpecMetadata(
                    action=ActionType.MODIFY,
                    name=f"update_{unique_id}",
                    uri="/api/vmm/v4.0.b1/ahv/config/vms/{extId}",
                    stop_on_error=True,
                    chunk_size=1,
                ),
                payload=batch_spec_payload_list,
            )

            print("Submitting batch operation to update existing VMs ...")
            batch_response = batch_instance.submit_batch(
                async_req=False, body=batch_spec
            )

            # grab the ext ID of the batch operation task
            modify_ext_id = batch_response.data.ext_id
            utils.monitor_task(
                task_ext_id=modify_ext_id,
                task_name="Batch VM Update",
                pc_ip=pc_ip,
                username=username,
                password=cluster_password,
                poll_timeout=poll_timeout,
            )
            print(f"{len(batch_spec_payload_list)} VMs updated.")
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
