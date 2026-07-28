"""
Use the Nutanix v4 Python SDK to assign Prism Central categories to VMs
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: June 2026
"""

import sys
import json
import os
import urllib3
from rich import print  # pylint: disable=line-too-long, redefined-builtin

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client import ApiClient as VMMClient
from ntnx_vmm_py_client.rest import ApiException as VMMException
import ntnx_vmm_py_client.models.vmm.v4.ahv.config as AhvVmConfig

import ntnx_prism_py_client
from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client.rest import ApiException as PrismException

# small library that manages commonly-used tasks across these code samples
from tme.utils import Utils


def load_json_file(filename: str) -> dict:
    """Load and parse a JSON file, returning the parsed content."""
    try:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as json_file:
                content = json.load(json_file)
                print(f"{filename} loaded successfully.")
                return content
        else:
            print(f"File {filename} not found.")
            sys.exit(1)
    except json.decoder.JSONDecodeError as json_error:
        print(f"Unable to load {filename}: {json_error}")
        sys.exit(1)


def get_vm_ext_id(vmm_instance, vm_name: str) -> str:
    """Retrieve VM ext_id by VM name."""
    try:
        print(f"Retrieving VM list to find {vm_name} ...")
        vms = vmm_instance.list_vms(async_req=False)
        for vm in vms.data:
            if vm.name.lower() == vm_name.lower():
                return vm.ext_id
        print(f"VM {vm_name} not found.")
        return None
    except VMMException as ex:
        print(f"Error retrieving VM list: {ex}")
        return None


def get_category_ext_id(prism_instance, key: str, value: str) -> str:
    """Retrieve category ext_id by key and value."""
    try:
        filter_string = f"key eq '{key}' and value eq '{value}'"
        categories = prism_instance.list_categories(
            _filter=filter_string, async_req=False
        )
        if categories.data and len(categories.data) > 0:
            return categories.data[0].ext_id
        print(f"Category {key}:{value} not found.")
        return None
    except PrismException as ex:
        print(f"Error retrieving category list: {ex}")
        return None


def main():  # noqa #pylint: disable=too-many-locals, too-many-branches, too-many-statements
    """
    suppress warnings about insecure connections
    consider the security implications before
    doing this in a production environment
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    utils = Utils()
    script_config = utils.get_environment()

    # create the configuration instances
    # this demo uses the `vmm` namespace to get VM details
    # and the `prism` namespace for category assignments
    vmm_config = VMMConfiguration()
    prism_config = PrismConfiguration()

    for config in [vmm_config, prism_config]:
        config.host = script_config.pc_ip
        config.port = "9440"
        config.username = script_config.pc_username
        config.password = script_config.pc_password
        config.verify_ssl = False

    # create the API client instances
    vmm_client = VMMClient(configuration=vmm_config)
    prism_client = PrismClient(configuration=prism_config)

    for client in [vmm_client, prism_client]:
        client.add_default_header(
            header_name="Accept-Encoding", header_value="gzip, deflate, br"
        )

    # create the API class instances
    vmm_instance = ntnx_vmm_py_client.api.VmApi(api_client=vmm_client)
    prism_instance = ntnx_prism_py_client.api.CategoriesApi(api_client=prism_client)

    # read the on-disk configuration files
    # this demo uses 2 files:
    #   - json file containing details of categories that
    #     will be assigned to VMs
    #   - json file containing details of VMs that will have
    #     categories assigned to them
    print("Loading JSON files ...\n")
    categories_data = load_json_file("assign_categories_to_vms_catspec.json")
    vms_data = load_json_file("assign_categories_to_vms_vmspec.json")

    print(
        f"Note: This script will assign {len(categories_data)} categor"
        f"{'y' if len(categories_data) == 1 else 'ies'} "
        f"to {len(vms_data)} VM{'s' if len(vms_data) != 1 else ''}."
    )
    confirm_assign = utils.confirm(
        "Assign categories to VMs?  "
        "This will make category changes in your environment."
    )

    if confirm_assign:
        print("Category assignment started ...\n")

        # track success and failures
        assignments_successful = 0
        assignments_failed = 0

        try:
            for vm_entry in vms_data:
                vm_name = vm_entry.get("name") or vm_entry.get("ext_id")
                if not vm_name:
                    print(
                        "VM entry missing 'name' or 'ext_id' field. "
                        "Skipping."
                    )
                    assignments_failed += 1
                    continue

                # get the VM's ext_id
                if "ext_id" in vm_entry:
                    vm_ext_id = vm_entry["ext_id"]
                else:
                    vm_ext_id = get_vm_ext_id(vmm_instance, vm_name)

                if not vm_ext_id:
                    print(f"Could not find ext_id for VM {vm_name}. Skipping.")
                    assignments_failed += 1
                    continue

                # retrieve the VM to get its Etag
                print(f"Retrieving VM details for {vm_name} ...")
                existing_vm = vmm_instance.get_vm_by_id(vm_ext_id)
                existing_vm_etag = vmm_client.get_etag(existing_vm)

                # add the Etag as If-Match header
                vmm_client.add_default_header(
                    header_name="If-Match", header_value=existing_vm_etag
                )
                # recreate the VmApi instance with the updated client
                vmm_instance = ntnx_vmm_py_client.api.VmApi(api_client=vmm_client)

                # build the category references list from the loaded data
                print(
                    f"Assigning {len(categories_data)} categor"
                    f"{'y' if len(categories_data) == 1 else 'ies'} "
                    f"to VM {vm_name} ..."
                )

                category_refs = []
                for category in categories_data:
                    category_key = category.get("key") or category.get("name")
                    category_value = category.get("value")

                    if not category_key or not category_value:
                        print(
                            "Category entry missing 'key'/'name' or "
                            "'value' field. "
                            "Skipping."
                        )
                        continue

                    # get the ext_id of the category from Prism Central
                    category_ext_id = get_category_ext_id(
                        prism_instance, category_key, category_value
                    )
                    if not category_ext_id:
                        print(
                            f"Could not find category "
                            f"{category_key}:{category_value}. "
                            "Skipping."
                        )
                        continue

                    # create a category reference with the ext_id
                    cat_ref = AhvVmConfig.CategoryReference.CategoryReference(
                        ext_id=category_ext_id
                    )
                    category_refs.append(cat_ref)
                    print(
                        f"  Adding category {category_key}:{category_value} "
                        f"(ext_id: {category_ext_id})"
                    )

                if not category_refs:
                    print(
                        f"No valid categories found for VM {vm_name}. "
                        "Skipping."
                    )
                    assignments_failed += 1
                    continue

                # create the AssociateVmCategoriesParams object
                associate_params = (
                    AhvVmConfig.AssociateVmCategoriesParams.AssociateVmCategoriesParams(  # noqa #pylint: disable=line-too-long, redefined-builtin
                        categories=category_refs
                    )
                )

                # associate the categories with the VM
                vmm_instance.associate_categories(
                    vm_ext_id, associate_params, async_req=False
                )
                assignments_successful += 1
                print(f"VM {vm_name} categories assigned successfully.\n")

        except AttributeError as ex:
            print("Attribute error while processing VM. Details:")
            print(ex)
            sys.exit(1)
        except KeyError as ex:
            print(f"KeyError: Missing required field. Details: {ex}")
            sys.exit(1)
        except (VMMException, PrismException) as ex:
            print("Error during category assignment. Details:")
            print(ex)
            assignments_failed += 1

        print(
            f"Category assignment complete. "
            f"Successful: {assignments_successful}, "
            f"Failed: {assignments_failed}"
        )
    else:
        print("Category assignment cancelled.")


if __name__ == "__main__":
    main()
