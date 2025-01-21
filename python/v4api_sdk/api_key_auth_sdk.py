"""
Use the Nutanix v4 API SDKs to setup API key authentication
Requires Prism Central 2024.3 or later and AOS 7.0 or later
"""

import getpass
import argparse
import sys
import urllib3
import json

import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client import ApiClient as VMMClient

import ntnx_iam_py_client
from ntnx_iam_py_client import Configuration as IAMConfiguration
from ntnx_iam_py_client import ApiClient as IAMClient
from ntnx_iam_py_client.rest import ApiException as IAMException

from ntnx_iam_py_client import UsersApi, AuthorizationPoliciesApi
from ntnx_iam_py_client import User, UserType, CreationType, UserStatusType
from ntnx_iam_py_client import Key, KeyKind
from ntnx_iam_py_client import AuthorizationPolicy, AuthorizationPolicyType
from ntnx_iam_py_client import EntityFilter, IdentityFilter

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

        vmm_config = VMMConfiguration()
        iam_config = IAMConfiguration()
        for config in [iam_config]:
            # create the configuration instances
            config.host = pc_ip
            config.username = username
            config.password = cluster_password
            config.verify_ssl = False
            config.debug = False

        # setup VMM configuration
        # note we are NOT setting the username and password at this time
        # later we will list VMs using API key authentication
        vmm_config.host = pc_ip
        vmm_config.port = "9440"
        vmm_config.verify_ssl = False
        vmm_config.debug = False

        vmm_config.logger_file = "./vmm.log"
        iam_config.logger_file = "./iam.log"

        # before configuring API key auth, we need to get
        # the extId of an existing role
        # for this demo, we will use the built-in 'Super Admin' role
        iam_client = IAMClient(configuration=iam_config)
        iam_instance = ntnx_iam_py_client.api.RolesApi(api_client=iam_client)
        print("Retrieving filtered role list ...")
        role_list = iam_instance.list_roles(
            async_req=False, _filter="contains(displayName, 'Super')"
        )
        if len(role_list.data) > 0:
            super_admin_ext_id = role_list.data[0].ext_id
            print(f"Super Admin role extId: {super_admin_ext_id}")
        else:
            print("No role found containing the word \"Super\".  Exiting ...")
            sys.exit()

        vmm_client = VMMClient(configuration=vmm_config)
        vmm_instance = ntnx_vmm_py_client.api.VmApi(api_client=vmm_client)

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

            iam_instance = UsersApi(api_client=iam_client)
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
            iam_instance = AuthorizationPoliciesApi(api_client=iam_client)
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
