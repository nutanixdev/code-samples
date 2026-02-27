"""
Use the Nutanix v4 API SDKs to demonstrate Prism batch MODIFY operations
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import getpass
import argparse
import sys
import uuid
import urllib3
from rich import print

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VmmConfiguration
from ntnx_vmm_py_client import ApiClient as VmmClient
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
        prism_config = PrismConfiguration()

        for config in [vmm_config, prism_config]:
            config.host = script_config.pc_ip
            config.port = "9440"
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False

        # create the instance of the ApiClient class
        vmm_client  = VmmClient(configuration=vmm_config)
        prism_client = PrismClient(configuration=prism_config)

        for client in [vmm_client, prism_client]:
            client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )

        # create the API class instances
        vmm_instance = ntnx_vmm_py_client.api.VmApi(api_client=vmm_client)
        prism_instance = ntnx_prism_py_client.api.BatchesApi(api_client=prism_client)

        # get an existing VM
        # for demo purposes we're filering specific VMs; for your environment
        # you will need to change this filter to suit your needs or specify
        # an exact VM ext_id
        print("Building filtered list of existing VMs ...")
        print("Note: By default this will retrieve a maximum of 50 VMs.")
        vm_list = vmm_instance.list_vms(
            async_req=False,
             _filter="startswith(name, 'batchdemo')"
        )
        if vm_list.data:
            print(f"{len(vm_list.data)} VM(s) found:")
            for vm in vm_list.data:
                print(f"- {vm.name}")
        else:
            print("No matching VMs found.  Exiting ...")
            sys.exit()

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
                    uri="/api/vmm/v4.2/ahv/config/vms/{extId}",
                    stop_on_error=True,
                    chunk_size=1,
                ),
                payload=batch_spec_payload_list,
            )

            print("Submitting batch operation to update existing VMs ...")
            batch_response = prism_instance.submit_batch(
                async_req=False, body=batch_spec
            )

            # grab the ext ID of the batch operation task
            modify_ext_id = batch_response.data.ext_id
            utils.monitor_task(
                task_ext_id=modify_ext_id,
                task_name="Batch VM Update",
                pc_ip=script_config.pc_ip,
                username=script_config.pc_username,
                password=script_config.pc_password,
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
