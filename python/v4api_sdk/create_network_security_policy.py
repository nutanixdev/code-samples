"""
Use the Nutanix v4 Python SDK to create a Nutanix Flow
Network Security Policy
Requires Prism Central pc.2024.1 or later and AOS 6.8 or later
"""

# disable pylint checks that don't matter for this demo
# pylint: disable=W0105, R0914, R0915;

import getpass
import argparse
import sys
from pprint import pprint
import urllib3

import ntnx_prism_py_client
import ntnx_microseg_py_client

from ntnx_microseg_py_client import Configuration as MicrosegConfiguration
from ntnx_microseg_py_client import ApiClient as MicrosegClient
from ntnx_microseg_py_client.rest import ApiException as MicrosegException

# alias the v4 microseg classes
# this is for demo purposes only and should be considered
# before using in a production script
import ntnx_microseg_py_client.models.microseg.v4.config as v4MicrosegConfig

from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client.rest import ApiException as PrismException


from tme.utils import Utils
from tme import Config


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
    except (PrismException, MicrosegException) as ex:
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
                "description": entity.description,
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
    consider the security implications before
    doing this in a production environment
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    """
    setup the command line parameters
    for this example only two parameters are required
    - the Prism Central IP address or FQDN
    - the Prism Central username; the script will prompt for
      the user's password
      so that it never needs to be stored in plain text
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("pc_ip", help="Prism Central IP address or FQDN")
    parser.add_argument("username", help="Prism Central username")
    args = parser.parse_args()

    # get the cluster password
    cluster_password = getpass.getpass(
        prompt="Please enter your Prism Central \
password: ",
        stream=None,
    )

    # create configuration instance; username, password, PC IP
    script_config = Config(
        pc_ip=args.pc_ip, pc_username=args.username, pc_password=cluster_password
    )

    # create utils instance for re-use later
    utils = Utils(
        pc_ip=script_config.pc_ip,
        username=script_config.pc_username,
        password=script_config.pc_password,
    )

    # make sure the user enters a password
    if not cluster_password:
        while not cluster_password:
            print(
                "Password cannot be empty.  \
    Please enter a password or Ctrl-C/Ctrl-D to exit."
            )
            cluster_password = getpass.getpass(
                prompt="Please enter your Prism Central \
password: ",
                stream=None,
            )

    prism_config = PrismConfiguration()
    microseg_config = MicrosegConfiguration()

    for config in [prism_config, microseg_config]:
        config.host = script_config.pc_ip
        config.username = script_config.pc_username
        config.password = script_config.pc_password
        config.verify_ssl = False
        config.logger_file = "./create_network_security_policy.log"

    prism_client = PrismClient(configuration=prism_config)
    microseg_client = MicrosegClient(configuration=microseg_config)

    for client in [prism_client, microseg_client]:
        client.add_default_header(
            header_name="Accept-Encoding", header_value="gzip, deflate, br"
        )

    input(
        "This demo creates a Two Environment Isolation Policy in MONITOR \
mode.  You will now be prompted for the ext_id of the two isolation groups \
that this policy's rule will apply to.  Note: In the context of this demo \
Isolation Groups are Prism Central categories; only USER type categories \
are included in the upcoming list.\n\nPress ENTER to continue."
    )

    """
    ask the user to confirm the first isolation group for the new policy
    """
    first_group_ext_id = confirm_entity(
        ntnx_prism_py_client.api.CategoriesApi, prism_client, "category"
    )

    """
    ask the user to confirm the second isolation group for the new policy
    """
    second_group_ext_id = confirm_entity(
        ntnx_prism_py_client.api.CategoriesApi, prism_client, "category"
    )

    # configure the new policy's specifications
    try:
        # https://developers.nutanix.com/api/v1/sdk/namespaces/main/microseg/versions/v4.0.a1/languages/python/ntnx_microseg_py_client.models.microseg.v4.config.NetworkSecurityPolicy.html#module-ntnx_microseg_py_client.models.microseg.v4.config.NetworkSecurityPolicy
        try:
            new_policy = v4MicrosegConfig.NetworkSecurityPolicy.NetworkSecurityPolicy(
                name="v4 SDK Network Security Policy",
                description="Network security policy created with the \
Nutanix v4 Flow Management SDKs; for demo purposes only!",
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
            async_req=False, body=new_policy
        )

        task_extid = create_policy.data.ext_id
        utils.monitor_task(
            task_ext_id=task_extid,
            task_name="Network Security Policy create",
            pc_ip=script_config.pc_ip,
            username=script_config.pc_username,
            password=script_config.pc_password,
            poll_timeout=1,
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
    else:
        print("Network Security Policy creation cancelled.")


if __name__ == "__main__":
    main()
