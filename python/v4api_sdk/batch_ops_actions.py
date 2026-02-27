"""
Use the Nutanix v4 API SDKs to demonstrate Prism batch ACTION operations
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import getpass
import argparse
import sys
import urllib3
from pprint import pprint
from rich import print

import ntnx_prism_py_client
from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client.rest import ApiException as PrismException

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VmmConfiguration
from ntnx_vmm_py_client import ApiClient as VmmClient
from ntnx_vmm_py_client.rest import ApiException as VMMException

from ntnx_vmm_py_client.models.vmm.v4.ahv.config.AssociateVmCategoriesParams import (
    AssociateVmCategoriesParams,
)
from ntnx_vmm_py_client.models.vmm.v4.ahv.config.CategoryReference import (
    CategoryReference,
)

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

        # create the API class instances
        vmm_instance = ntnx_vmm_py_client.api.VmApi(api_client=vmm_client)
        prism_instance = ntnx_prism_py_client.api.CategoriesApi(api_client=prism_client)
        batch_instance = ntnx_prism_py_client.api.BatchesApi(api_client=prism_client)


        input(
            "\nThis demo uses the Nutanix v4 API `prism` namespace's \
batch APIs to assign matching virtual machines to a specific \
category.\nVM matches are based on a list of VMs built using OData \
filters to include those with a name containing the string \
'batchdemo'.\n\nYou will now be prompted for the ext_id of the category \
to which these VMs will be assigned.\n\nPress ENTER to continue."
        )

        category_list = prism_instance.list_categories(
            async_req=False,
            _filter="type eq Prism.Config.CategoryType'USER' and not contains(key, 'Calm')",
        )

        # do some verification and make sure the user selects
        # the correct entity
        found_categories = []
        for category in category_list.data:
            found_categories.append(
                {
                    "key": category.key,
                    "value": category.value,
                    "ext_id": category.ext_id,
                }
            )
        print(f"The following categories ({len(found_categories)}) were found.")
        pprint(found_categories)

        expected_category_ext_id = input(
        "\nPlease enter the ext_id of the selected category: ").lower()
        matches = [
            category
            for category in found_categories
            if category["ext_id"].lower() == expected_category_ext_id.lower()
        ]
        if not matches:
            print(
                f"No category was found matching the ext_id \
    {expected_category_ext_id}.  Exiting."
            )
            sys.exit()
        # get the category ext_id
        category_ext_id = matches[0]["ext_id"]

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

        confirm_action = utils.confirm("Submit batch operation?")
        if confirm_action:
            # initiate the list of VMs that will be modified
            # this is a list of BatchSpecPayload
            batch_spec_payload_list = []

            print("Building VM batch $action payload ...")
            for vm in vm_list.data:
                existing_vm = vmm_instance.get_vm_by_id(vm.ext_id)
                vm_ext_id = existing_vm.data.ext_id
                etag = vmm_client.get_etag(existing_vm)

                # build the payload that will be used when assigning categories
                batch_spec_payload_list.append(
                    BatchSpecPayload(
                        data=AssociateVmCategoriesParams(
                            categories=[CategoryReference(ext_id=category_ext_id)]
                        ),
                        metadata=BatchSpecPayloadMetadata(
                            headers=[
                                BatchSpecPayloadMetadataHeader(
                                    name="If-Match", value=etag
                                )
                            ],
                            path=[
                                BatchSpecPayloadMetadataPath(
                                    name="extId", value=vm_ext_id
                                )
                            ],
                        ),
                    )
                )

            batch_spec = BatchSpec(
                metadata=BatchSpecMetadata(
                    action=ActionType.ACTION,
                    name="Associate Categories",
                    stop_on_error=True,
                    chunk_size=1,
                    uri="/api/vmm/v4.2/ahv/config/vms/{extId}/$actions/associate-categories",
                ),
                payload=batch_spec_payload_list,
            )

            print("Submitting batch operation to assign VM categories ...")
            batch_response = batch_instance.submit_batch(
                async_req=False, body=batch_spec
            )

            # grab the ext ID of the batch operation task
            modify_ext_id = batch_response.data.ext_id
            utils.monitor_task(
                task_ext_id=modify_ext_id,
                task_name="Batch VM Category Assignment",
                pc_ip=script_config.pc_ip,
                username=script_config.pc_username,
                password=script_config.pc_password,
            )
            print(f"{len(batch_spec_payload_list)} VMs assigned to category.")
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
