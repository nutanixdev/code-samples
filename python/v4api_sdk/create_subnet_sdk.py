"""
Use the Nutanix v4 Python SDK to create a Prism Central managed subnet
Requires Prism Central pc.2024.1 or later and AOS 6.8 or later
"""

# disable pylint checks that don't matter for this demo
# pylint: disable=W0105, R0914, R0915;

import getpass
import argparse
import sys
import json
import os
from pprint import pprint
import urllib3

import ntnx_networking_py_client
import ntnx_clustermgmt_py_client

from ntnx_networking_py_client import Configuration as NetworkingConfiguration
from ntnx_networking_py_client import ApiClient as NetworkingClient
from ntnx_networking_py_client.rest import ApiException as NetworkingException

# alias the v1 common and v4 networking classes
# this is for demo purposes only and should be considered
# before using in a production script
import ntnx_networking_py_client.models.common.v1.config as v1CommonConfig
import ntnx_networking_py_client.models.networking.v4.config as v4NetConfig

from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient
from ntnx_clustermgmt_py_client.rest import ApiException as ClusterException

from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client.rest import ApiException as PrismException


from tme.utils import Utils
from tme.utils import Config


def confirm_entity(api, client, entity_name: str, exclusions: list) -> str:
    """
    make sure the user is selecting the correct entity
    e.g. the cluster that will own the VM, the image to
    clone the VM's base disk from
    this is moved into a function as the same steps are completed
    multiple times for different entity types
    """
    instance = api(api_client=client)
    print(f"Retrieving {entity_name} list ...")
    offset = 0

    try:
        if entity_name == "cluster":
            entities = instance.list_clusters(async_req=False)
            offset = 1
        elif entity_name == "image":
            entities = instance.list_images(async_req=False)
        elif entity_name == "subnet":
            entities = instance.list_subnets(async_req=False)
        else:
            print(f"{entity_name} is not supported.  Exiting.")
            sys.exit()
    except (ClusterException, PrismException, NetworkingException) as ex:
        print(
            f"\nAn exception occurred while retrieving the {entity_name} list.\
  Details:\n"
        )
        print(ex)
        sys.exit()

    # do some verification and make sure the user selects
    # the correct entity
    found_entities = []
    for entity in entities.data:
        if entity.name not in exclusions:
            found_entities.append({"name": entity.name, "ext_id": entity.ext_id})
    print(f"The following {entity_name}s ({len(entities.data)-offset}) were found.")
    pprint(found_entities)
    expected_entity_name = input(
        f"\nPlease enter the name of the selected {entity_name}: "
    ).lower()
    matches = [
        x for x in found_entities if x["name"].lower() == expected_entity_name.lower()
    ]
    if not matches:
        print(
            f"No {entity_name} was found matching the name {expected_entity_name}.  Exiting."
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
    parser.add_argument(
        "subnet_config", help="Subnet specifications file in JSON format"
    )
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

    subnet_config = args.subnet_config

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

    # load the configuration
    print(f"Loading subnet configuration from {subnet_config} ...")
    try:
        if os.path.exists(subnet_config):
            with open(subnet_config, "r", encoding="utf-8") as config_file:
                config_json = json.loads(config_file.read())
                print("Subnet configuration loaded successfully.")
        else:
            print(f"Configuration file {subnet_config} not found.")
            sys.exit()
    except json.decoder.JSONDecodeError as config_error:
        print(f"Unable to load configuration: {config_error}")
        sys.exit()

    networking_config = NetworkingConfiguration()
    cluster_config = ClusterConfiguration()
    prism_config = PrismConfiguration()

    for config in [networking_config, cluster_config, prism_config]:
        config.host = script_config.pc_ip
        config.username = script_config.pc_username
        config.password = script_config.pc_password
        config.verify_ssl = False

    networking_client = NetworkingClient(configuration=networking_config)
    cluster_client = ClusterClient(configuration=cluster_config)
    prism_client = PrismClient(configuration=prism_config)

    for client in [networking_client, cluster_client, prism_client]:
        client.add_default_header(
            header_name="Accept-Encoding", header_value="gzip, deflate, br"
        )

    """
    ask the user to confirm the cluster that will own the subnet
    """
    cluster_ext_id = confirm_entity(
        ntnx_clustermgmt_py_client.api.ClustersApi,
        cluster_client,
        "cluster",
        ["Unnamed"],
    )

    # configure the new subnet's specifications
    # these specs are based on those loaded from the command-line JSON file
    try:
        # https://developers.nutanix.com/api/v1/sdk/namespaces/main/networking/versions/v4.0.b1/languages/python/ntnx_networking_py_client.models.networking.v4.config.Subnet.html#module-ntnx_networking_py_client.models.networking.v4.config.Subnet
        try:
            new_subnet = v4NetConfig.Subnet.Subnet(
                name=config_json["name"],
                description=config_json["description"],
                cluster_reference=cluster_ext_id,
                subnet_type=v4NetConfig.SubnetType.SubnetType.VLAN,
                network_id=config_json["network_id"],
                virtual_switch_reference=config_json["virtual_switch_reference"],
                is_external=config_json["is_external"],
                is_advanced_networking=config_json["is_advanced_networking"],
                dhcp_options=v4NetConfig.DhcpOptions.DhcpOptions(
                    domain_name_servers=[
                        v1CommonConfig.IPAddress.IPAddress(
                            ipv4=v1CommonConfig.IPv4Address.IPv4Address(
                                prefix_length=config_json["dhcp"]["dns_servers"][0][
                                    "prefix_length"
                                ],
                                value=config_json["dhcp"]["dns_servers"][0][
                                    "ip_address"
                                ],
                            )
                        ),
                        v1CommonConfig.IPAddress.IPAddress(
                            ipv4=v1CommonConfig.IPv4Address.IPv4Address(
                                prefix_length=config_json["dhcp"]["dns_servers"][1][
                                    "prefix_length"
                                ],
                                value=config_json["dhcp"]["dns_servers"][1][
                                    "ip_address"
                                ],
                            )
                        ),
                    ]
                ),
                ip_config=[
                    v4NetConfig.IPConfig.IPConfig(
                        ipv4=v4NetConfig.IPv4Config.IPv4Config(
                            default_gateway_ip=v1CommonConfig.IPv4Address.IPv4Address(
                                prefix_length=config_json["gateway"]["prefix_length"],
                                value=config_json["gateway"]["ip_address"],
                            ),
                            dhcp_server_address=v1CommonConfig.IPv4Address.IPv4Address(
                                prefix_length=config_json["dhcp"]["dhcp_server"][
                                    "prefix_length"
                                ],
                                value=config_json["dhcp"]["dhcp_server"]["ip_address"],
                            ),
                            ip_subnet=v4NetConfig.IPv4Subnet.IPv4Subnet(
                                ip=v1CommonConfig.IPv4Address.IPv4Address(
                                    prefix_length=config_json["subnet_ip_prefix"],
                                    value=config_json["subnet_ip_address"],
                                ),
                                prefix_length=config_json["subnet_prefix"],
                            ),
                            pool_list=[
                                v4NetConfig.IPv4Pool.IPv4Pool(
                                    end_ip=v1CommonConfig.IPv4Address.IPv4Address(
                                        prefix_length=config_json["dhcp"]["dhcp_pool"][
                                            "end_ip"
                                        ]["prefix_length"],
                                        value=config_json["dhcp"]["dhcp_pool"][
                                            "end_ip"
                                        ]["ip_address"],
                                    ),
                                    start_ip=v1CommonConfig.IPv4Address.IPv4Address(
                                        prefix_length=config_json["dhcp"]["dhcp_pool"][
                                            "start_ip"
                                        ]["prefix_length"],
                                        value=config_json["dhcp"]["dhcp_pool"][
                                            "start_ip"
                                        ]["ip_address"],
                                    ),
                                )
                            ],
                        )
                    )
                ],
            )
        except AttributeError as ex:
            print("Attribute error while creating new subnet instance.  Details:")
            print(ex)
            sys.exit()
    except KeyError:
        print(
            f"KeyError: {subnet_config} does not contain the required keys.  \
Check the format then try again."
        )
        sys.exit()

    # ask if the user really wants to create the subnet
    confirm_create = utils.confirm(
        "Create subnet?  This will make networking changes in your environment."
    )

    # did the user say Yes to creating the subnet?
    if confirm_create:
        networking_instance = ntnx_networking_py_client.api.SubnetsApi(
            api_client=networking_client
        )

        print("\nCreating Subnet ...")
        create_subnet = networking_instance.create_subnet(
            async_req=False, body=new_subnet
        )

        task_extid = create_subnet.data.ext_id
        utils.monitor_task(
            task_ext_id=task_extid,
            task_name="Subnet create",
            pc_ip=script_config.pc_ip,
            username=script_config.pc_username,
            password=script_config.pc_password,
            poll_timeout=1,
            prefix="",
        )
        print(f"New Subnet named {config_json['name']} has been created.\n")
    else:
        print("Subnet creation cancelled.")


if __name__ == "__main__":
    main()
