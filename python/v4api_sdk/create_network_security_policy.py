"""
Use the Nutanix v4 Python SDK to create a Nutanix Flow Network Security Policy
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

# disable pylint checks that don't matter for this demo
# pylint: disable=W0105, R0914, R0915;

import getpass
import argparse
import sys
from pprint import pprint
import urllib3
from rich import print

import ntnx_prism_py_client
from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client.rest import ApiException as PrismException

import ntnx_microseg_py_client
from ntnx_microseg_py_client import Configuration as MicrosegConfiguration
from ntnx_microseg_py_client import ApiClient as MicrosegClient
from ntnx_microseg_py_client.rest import ApiException as MicrosegException

# alias the v4 microseg classes
# this is for demo purposes only and should be considered
# before using in a production script
import ntnx_microseg_py_client.models.microseg.v4.config as v4MicrosegConfig

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

    input(
        "This demo creates a Two Environment Isolation Policy in MONITOR \
mode.  You will now be prompted for the ext_id of the two isolation groups \
that this policy's rule will apply to.  Note: In the context of this demo \
Isolation Groups are Prism Central categories; only USER type categories \
are included in the upcoming list.\n\nPress ENTER to continue.\n"
    )

    prism_config = PrismConfiguration()
    microseg_config = MicrosegConfiguration()

    for config in [prism_config, microseg_config]:
        config.host = script_config.pc_ip
        config.username = script_config.pc_username
        config.password = script_config.pc_password
        config.verify_ssl = False

    prism_client = PrismClient(configuration=prism_config)
    microseg_client = MicrosegClient(configuration=microseg_config)

    for client in [prism_client, microseg_client]:
        client.add_default_header(
            header_name="Accept-Encoding",
            header_value="gzip, deflate, br"
        )

    # create the API class instances
    # prism_instance = ntnx_prism_py_client.api.CategoriesApi(api_client=prism_client)

    # list existing categories
    # we need to know which categories already exist so the user
    # can select the categories to use in the new security policy
    category_list = prism_instance.list_categories(
        async_req=False,
        _filter="type eq Prism.Config.CategoryType'USER' and not contains(key, 'Calm')",
    )

    # list the categories for the user to choose from
    category_ext_id_list = []
    for category in category_list.data:
        print(f"Category key: {category.key}, value: {category.value}, ext_id: {category.ext_id}")
        category_ext_id_list.append(category.ext_id)

    # get the category IDs from the user
    first_group_ext_id = input(
        "\nEnter the ext_id for the first Network Security Policy category: "
    )
    second_group_ext_id = input(
        "Enter the ext_id for the second Network Security Policy category: "
    )

    if first_group_ext_id == second_group_ext_id:
        print("The first and second category ext_id are the same; they must be different for this demo to function as expected.  Exiting.")
        sys.exit()
    elif first_group_ext_id not in category_ext_id_list or second_group_ext_id not in category_ext_id_list:
        print("One of the categories is not in the list of categories found in your Prism Central instance.  Exiting.")
        sys.exit()

    # configure the new policy's specifications
    try:
        try:
            new_policy = v4MicrosegConfig.NetworkSecurityPolicy.NetworkSecurityPolicy(
                name="v4 SDK Network Security Policy",
                description="Network Security Policy via SDK",
                type=v4MicrosegConfig.SecurityPolicyType.SecurityPolicyType.ISOLATION,
                state=v4MicrosegConfig.SecurityPolicyState.SecurityPolicyState.MONITOR,
                rules=[
                    v4MicrosegConfig.NetworkSecurityPolicyRule.NetworkSecurityPolicyRule(
                        description="First network security policy rule",
                        spec=v4MicrosegConfig.TwoEnvIsolationRuleSpec.TwoEnvIsolationRuleSpec(
                            first_isolation_group=[first_group_ext_id],
                            second_isolation_group=[second_group_ext_id],
                        ),
                        type=v4MicrosegConfig.RuleType.RuleType.TWO_ENV_ISOLATION,
                    )
                ],
            )
        except AttributeError as ex:
            print(
                "Attribute error while creating new policy instance. \
Details:"
            )
            print(ex)
            sys.exit()
    except MicrosegException as ex:
        print("Exception while creating new policy instance.  Details:")
        print(ex)
        sys.exit()

    # ask if the user really wants to create the policy
    confirm_create = utils.confirm(
        "Create Network Security Policy?  This will make Nutanix Flow Network \
Security changes in your environment."
    )

    # did the user say Yes to creating the policy?
    if confirm_create:
        microseg_instance = ntnx_microseg_py_client.api.NetworkSecurityPoliciesApi(
            api_client=microseg_client
        )

        print("\nCreating Network Security Policy ...")
        create_policy = microseg_instance.create_network_security_policy(
            async_req=False,
            body=new_policy
        )

        task_extid = create_policy.data.ext_id
        utils.monitor_task(
            task_ext_id=task_extid,
            task_name="Network Security Policy create",
            pc_ip=script_config.pc_ip,
            username=script_config.pc_username,
            password=script_config.pc_password,
            prefix="",
        )
        prism_instance = ntnx_prism_py_client.api.TasksApi(api_client=prism_client)
        new_policy_ext_id = (
            prism_instance.get_task_by_id(task_extid).data.entities_affected[0].ext_id
        )
        print(
            f"New Network Security Policy named {new_policy.name} has been \
created with ext_id {new_policy_ext_id}.\n"
        )
        print("NOTE: The new Network Security Policy has been created in MONITOR mode.")
    else:
        print("Network Security Policy creation cancelled.")


if __name__ == "__main__":
    main()
