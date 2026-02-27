"""
Use the Nutanix v4 API SDKs to setup API key authentication
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import getpass
import argparse
import sys
import urllib3
import json
from rich import print

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VmmConfiguration
from ntnx_vmm_py_client import ApiClient as VmmClient
from ntnx_vmm_py_client.rest import ApiException as VMMException

import ntnx_iam_py_client
from ntnx_iam_py_client import Configuration as IamConfiguration
from ntnx_iam_py_client import ApiClient as IamClient
from ntnx_iam_py_client.rest import ApiException as IAMException

from ntnx_iam_py_client import AuthorizationPoliciesApi
from ntnx_iam_py_client import User, UserType, CreationType, UserStatusType
from ntnx_iam_py_client import Key, KeyKind
from ntnx_iam_py_client import AuthorizationPolicy, AuthorizationPolicyType
from ntnx_iam_py_client import EntityFilter, IdentityFilter

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
        iam_config = IamConfiguration()

        for config in [vmm_config, iam_config]:
            config.host = script_config.pc_ip
            config.port = "9440"
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False

        # create the instance of the ApiClient class
        vmm_client  = VmmClient(configuration=vmm_config)
        iam_client = IamClient(configuration=iam_config)

        # create the instance of the ImagesApi class
        # this example uses the ImagesApi, since we want to
        # demonstrate listing Prism Central images
        vmm_instance = ntnx_vmm_py_client.api.VmApi(api_client=vmm_client)
        iam_instance = ntnx_iam_py_client.api.RolesApi(api_client=iam_client)

        print("Retrieving filtered role list ...")
        role_list = iam_instance.list_roles(
            async_req=False,
            _filter="contains(displayName, 'Super')"
        )
        if len(role_list.data) > 0:
            super_admin_ext_id = role_list.data[0].ext_id
            print(f"Super Admin role extId: {super_admin_ext_id}")
        else:
            print("No role found containing the word \"Super\".  Exiting ...")
            sys.exit()

        sa_username = "api_key_service_account"
        sa_email = "<email_address_here>"
        sa_display_name = "API key service account"
        sa_description = "Service account for API key authentication"
        key_name = "service_account_api_key"
        acp_display_name = "API Key Auth Policy"

        print("\nThe following configuration will be used for API key authentication.")
        print(f"    Username: {sa_username}")
        print(f"    Description: {sa_description}")
        print(f"    Email: {sa_email}")
        print(f"    Display name: {sa_display_name}")
        print(f"    Key name: {key_name}")
        print(f"    Authorization policy display name: {acp_display_name}\n")

        confirm_continue = utils.confirm("Continue API key configuration?")

        if confirm_continue:
            # create service account
            service_account = User(
                username=sa_username,
                email=sa_email,
                display_name=sa_display_name,
                description=sa_description,
                creation_type=CreationType.USERDEFINED,
                status=UserStatusType.ACTIVE,
                user_type=UserType.SERVICE_ACCOUNT,
            )

            iam_instance = ntnx_iam_py_client.api.UsersApi(api_client=iam_client)
            create_sa = iam_instance.create_user(async_req=False, body=service_account)

            if create_sa:
                print("Service account created successfully.")
            else:
                print("Service account creation failed.  Check iam.log for details.")
                sys.exit()

            # get the new service account user's ext_id
            sa_ext_id = create_sa.data.ext_id

            # create API key
            api_key = Key(name=key_name, key_type=KeyKind.API_KEY)

            create_key = iam_instance.create_user_key(
                async_req=False, userExtId=sa_ext_id, body=api_key
            )
            if create_key:
                print("API key created successfully.")
                print(
                    f"The API key will only be shown ONCE: {create_key.data.key_details.api_key}"
                )
                api_key_value = create_key.data.key_details.api_key

            entities = [EntityFilter({"*": {"*": {"eq": "*"}}})]

            identities = [IdentityFilter({"user": {"uuid": {"anyof": [sa_ext_id]}}})]

            # create authorization policy for new service account
            iam_instance = ntnx_iam_py_client.api.AuthorizationPoliciesApi(api_client=iam_client)
            auth_policy = AuthorizationPolicy(
                display_name=acp_display_name,
                description="Authorization policy for use with API key service accounts",
                authorization_policy_type=AuthorizationPolicyType.USER_DEFINED,
                entities=entities,
                identities=identities,
                role=super_admin_ext_id,
            )

            create_acp = iam_instance.create_authorization_policy(
                async_req=False, body=auth_policy
            )
            if create_acp:
                print("Authorization policy created successfully.")
            else:
                print(
                    "Authorization policy creation failed.  Check iam.log for details."
                )

            auth_with_key = utils.confirm(
                "\nAll configuration completed successfully.  Attempt to list VMs with API authentication?"
            )
            if auth_with_key:
                print(
                    "Attempting to list Prism Central VMs using API key authentication ..."
                )
                vmm_client.add_default_header(
                    header_name="X-Ntnx-Api-Key", header_value=api_key_value
                )
                vm_list = vmm_instance.list_vms(async_req=False)
                if vm_list:
                    print(
                        f"{len(vm_list.data)} VMs found.  API key authentication successful."
                    )
                else:
                    print("VM list operation failed.  Check vmm.log for details.")
            else:
                print("API key authentication cancelled.")
        else:
            print("API key configuration cancelled.")
            sys.exit()

    except IAMException as iam_exception:
        print(
            f"Error sending request. Exception details:\n    {json.loads(iam_exception.body)['data']['error'][0]['message']}"
        )

if __name__ == "__main__":
    main()
