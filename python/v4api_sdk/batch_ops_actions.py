"""
Use the Nutanix v4 API SDKs to demonstrate Prism batch ACTION operations
Requires Prism Central 2024.1 or later and AOS 6.8 or later
"""

import getpass
import argparse
import sys
import urllib3
from pprint import pprint

import ntnx_prism_py_client
from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client.rest import ApiException as PrismException

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client import ApiClient as VMMClient
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


from tme.utils import Utils


def confirm_entity(api, client, entity_name: str) -> str:
    """
    make sure the user is selecting the correct entity
    """
    instance = api(api_client=client)
    print(f"Retrieving {entity_name} list ...")

    try:
        if entity_name == "category":
            # this filter is specific to this code sample and would need
            # to be modified before use elsewhere
            entities = instance.list_categories(
                async_req=False,
                _filter="type eq Schema.Enums.CategoryType'USER' and not contains(key, 'Calm')",
            )
        else:
            print(f"{entity_name} is not supported.  Exiting.")
            sys.exit()
    except PrismException as ex:
        print(
            f"\nAn exception occurred while retrieving the {entity_name} list.\
  Details:\n"
        )
        print(ex)
        sys.exit()
    except urllib3.exceptions.MaxRetryError as ex:
        print(
            f"Error connecting to {client.configuration.host}.  Check connectivity, then try again.  Details:"
        )
        print(ex)
        sys.exit()

    # do some verification and make sure the user selects
    # the correct entity
    found_entities = []
    for entity in entities.data:
        found_entities.append(
            {
                "key": entity.key,
                "value": entity.value,
                "ext_id": entity.ext_id,
            }
        )
    print(f"The following categories ({len(found_entities)}) were found.")
    pprint(found_entities)

    expected_entity_ext_id = input(
        f"\nPlease enter the ext_id of the selected {entity_name}: "
    ).lower()
    matches = [
        x
        for x in found_entities
        if x["ext_id"].lower() == expected_entity_ext_id.lower()
    ]
    if not matches:
        print(
            f"No {entity_name} was found matching the ext_id \
{expected_entity_ext_id}.  Exiting."
        )
        sys.exit()
    # get the entity ext_id
    ext_id = matches[0]["ext_id"]
    return ext_id


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

        prism_client = PrismClient(configuration=prism_config)
        vmm_client = VMMClient(configuration=vmm_config)

        batch_instance = ntnx_prism_py_client.api.BatchesApi(api_client=prism_client)
        vmm_instance = ntnx_vmm_py_client.api.VmApi(api_client=vmm_client)

        input(
            "\nThis demo uses the Nutanix v4 API `prism` namespace's \
batch APIs to assign matching virtual machines to a specific \
category.\nVM matches are based on a list of VMs built using OData \
filters to include those with a name containing the string \
'batchdemo'.\n\nYou will now be prompted for the ext_id of the category \
to which these VMs will be assigned.\n\nPress ENTER to continue."
        )

        """
        ask the user to confirm the category ext_id
        """
        category_ext_id = confirm_entity(
            ntnx_prism_py_client.api.CategoriesApi, prism_client, "category"
        )

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
                    uri="/api/vmm/v4.0.b1/ahv/config/vms/{extId}/$actions/associate-categories",
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
                pc_ip=pc_ip,
                username=username,
                password=cluster_password,
                poll_timeout=poll_timeout,
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
