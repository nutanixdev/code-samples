"""
Use the Nutanix v4 REST API, via the Python requests library, to assign
Prism Central categories to VMs
This is a "no SDK" version of assign_categories_to_vms_sdk.py and carries out
the identical operation using direct HTTPS calls
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: July 2026
"""

import sys
import json
import os
import uuid
import argparse
import getpass
from dataclasses import dataclass

import urllib3
import requests
from requests.auth import HTTPBasicAuth
from rich import print  # pylint: disable=line-too-long, redefined-builtin

# API versions, matching the namespaces used by the SDK version of this script
VMM_API_VERSION = "v4.2"
PRISM_API_VERSION = "v4.3"


@dataclass
class Config:
    """dataclass to hold configuration for each script run."""

    pc_ip: str
    pc_username: str
    pc_password: str


def get_environment() -> Config:
    """
    setup the command line parameters
    the script prompts for the password so that it never needs to be
    stored in plain text
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pc_ip", required=True, help="Prism Central IP address or FQDN"
    )
    parser.add_argument("--username", required=True, help="Prism Central username")
    args = parser.parse_args()

    cluster_password = getpass.getpass(
        prompt="Enter your Prism Central password: ", stream=None
    )
    while not cluster_password:
        print("Password cannot be empty. Enter a password or Ctrl-C/Ctrl-D to exit.")
        cluster_password = getpass.getpass(
            prompt="Enter your Prism Central password: ", stream=None
        )

    return Config(
        pc_ip=args.pc_ip,
        pc_username=args.username,
        pc_password=cluster_password,
    )


def confirm(message: str) -> bool:
    """request a yes/NO confirmation from the user."""
    yes_no = input(f"{message} (yes/NO): ").lower()
    return yes_no == "yes"


class PrismSession:
    """
    thin wrapper around requests.Session that handles the parts the SDK
    would normally take care of: base URL construction, basic auth,
    default headers and TLS verification
    """

    def __init__(self, pc_ip: str, username: str, password: str, port: str = "9440"):
        self.base_url = f"https://{pc_ip}:{port}/api"
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.verify = False
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip, deflate, br",
            }
        )

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        """send a request and raise on any non-success status code."""
        response = self.session.request(
            method, f"{self.base_url}{path}", timeout=30, **kwargs
        )
        response.raise_for_status()
        return response


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


def get_vm_ext_id(prism: PrismSession, vm_name: str) -> str:
    """Retrieve VM ext_id by VM name."""
    try:
        print(f"Retrieving VM list to find {vm_name} ...")
        page = 0
        while True:
            response = prism.request(
                "GET",
                f"/vmm/{VMM_API_VERSION}/ahv/config/vms",
                params={"$page": page, "$limit": 100},
            )
            vms = response.json().get("data") or []
            if not vms:
                break
            for vm in vms:
                if vm.get("name", "").lower() == vm_name.lower():
                    return vm["extId"]
            page += 1
        print(f"VM {vm_name} not found.")
        return None
    except requests.exceptions.RequestException as ex:
        print(f"Error retrieving VM list: {ex}")
        return None


def get_category_ext_id(prism: PrismSession, key: str, value: str) -> str:
    """Retrieve category ext_id by key and value."""
    try:
        filter_string = f"key eq '{key}' and value eq '{value}'"
        response = prism.request(
            "GET",
            f"/prism/{PRISM_API_VERSION}/config/categories",
            params={"$filter": filter_string},
        )
        categories = response.json().get("data") or []
        if categories:
            return categories[0]["extId"]
        print(f"Category {key}:{value} not found.")
        return None
    except requests.exceptions.RequestException as ex:
        print(f"Error retrieving category list: {ex}")
        return None


def get_vm_etag(prism: PrismSession, vm_ext_id: str) -> str:
    """
    Retrieve a VM and return its ETag
    the v4 API returns the ETag as a response header, with a copy in the
    response body's $reserved section; this is the manual equivalent of
    the SDK's ApiClient.get_etag() helper
    """
    response = prism.request(
        "GET", f"/vmm/{VMM_API_VERSION}/ahv/config/vms/{vm_ext_id}"
    )
    etag = response.headers.get("ETag")
    if not etag:
        reserved = response.json().get("$reserved") or {}
        etag = reserved.get("ETag")
    return etag


def main():  # noqa #pylint: disable=too-many-locals, too-many-branches, too-many-statements
    """
    suppress warnings about insecure connections
    consider the security implications before
    doing this in a production environment
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    script_config = get_environment()

    # a single session covers both the vmm and prism namespaces
    # the namespace is part of the request path rather than the client
    prism = PrismSession(
        pc_ip=script_config.pc_ip,
        username=script_config.pc_username,
        password=script_config.pc_password,
    )

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
    confirm_assign = confirm(
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
                    vm_ext_id = get_vm_ext_id(prism, vm_name)

                if not vm_ext_id:
                    print(f"Could not find ext_id for VM {vm_name}. Skipping.")
                    assignments_failed += 1
                    continue

                # retrieve the VM to get its Etag
                print(f"Retrieving VM details for {vm_name} ...")
                existing_vm_etag = get_vm_etag(prism, vm_ext_id)

                if not existing_vm_etag:
                    print(f"Could not retrieve ETag for VM {vm_name}. Skipping.")
                    assignments_failed += 1
                    continue

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
                        prism, category_key, category_value
                    )
                    if not category_ext_id:
                        print(
                            f"Could not find category "
                            f"{category_key}:{category_value}. "
                            "Skipping."
                        )
                        continue

                    # create a category reference with the ext_id
                    # the $objectType field replaces the SDK's typed model class
                    category_refs.append(
                        {
                            "extId": category_ext_id,
                            "$objectType": "vmm.v4.ahv.config.CategoryReference",
                        }
                    )
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

                # create the AssociateVmCategoriesParams payload
                associate_params = {
                    "categories": category_refs,
                    "$objectType": (
                        "vmm.v4.ahv.config.AssociateVmCategoriesParams"
                    ),
                }

                # associate the categories with the VM
                # the If-Match and NTNX-Request-Id headers are mandatory and
                # are normally supplied by the SDK on the caller's behalf
                prism.request(
                    "POST",
                    f"/vmm/{VMM_API_VERSION}/ahv/config/vms/{vm_ext_id}"
                    "/$actions/associate-categories",
                    headers={
                        "If-Match": existing_vm_etag,
                        "NTNX-Request-Id": str(uuid.uuid4()),
                    },
                    json=associate_params,
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
        except requests.exceptions.RequestException as ex:
            print("Error during category assignment. Details:")
            print(ex)
            if ex.response is not None:
                print(ex.response.text)
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
