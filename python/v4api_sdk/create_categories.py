"""
Use the Nutanix v4 Python SDK to create a collection of
Prism Central categories
Requires Prism Central pc.2024.1 or later and AOS 6.8 or later
"""

# disable pylint checks that don't matter for this demo
# pylint: disable=W0105, R0912, R0914, R0915;

import getpass
import argparse
import sys
import json
import os
import urllib3

import ntnx_prism_py_client

from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client.rest import ApiException as PrismException


from tme.utils import Utils
from tme import Config


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
        "category_specs", help="Category specifications file in JSON format"
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

    category_specs = args.category_specs

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
    print(f"Loading category specs from {category_specs} ...")
    try:
        if os.path.exists(category_specs):
            with open(category_specs, "r", encoding="utf-8") as spec_file:
                spec_json = json.loads(spec_file.read())
                print("Category specs loaded successfully.")
        else:
            print(f"Category specs file {category_specs} not found.")
            sys.exit()
    except json.decoder.JSONDecodeError as spec_error:
        print(f"Unable to load category specs: {spec_error}")
        sys.exit()

    prism_config = PrismConfiguration()

    for config in [prism_config]:
        config.host = script_config.pc_ip
        config.username = script_config.pc_username
        config.password = script_config.pc_password
        config.verify_ssl = False

    prism_client = PrismClient(configuration=prism_config)

    for client in [prism_client]:
        client.add_default_header(
            header_name="Accept-Encoding", header_value="gzip, deflate, br"
        )

    prism_instance = ntnx_prism_py_client.api.CategoriesApi(api_client=prism_client)

    # ask if the user really wants to create the categories
    print(
        f"Note: Prism Central categories must be unique.  Running this \
script more than once without editing the category names and values in \
{category_specs} will throw a PrismException."
    )
    confirm_create = utils.confirm(
        "Create categories?  This will make category changes in your \
environment."
    )

    if confirm_create:
        print("Category creation started ...\n")

        # iterate over the list of categories that have been loaded from the
        # specs file
        # for each loaded category, create a new Prism Central category

        try:
            for category in spec_json:
                # create a new Prism Central category instance
                print(
                    f"Create category {category['name']}:\
{category['value']} description {category['description']} ..."
                )
                # https://developers.nutanix.com/api/v1/sdk/namespaces/main/prism/versions/v4.0.a2/languages/python/ntnx_prism_py_client.models.prism.v4.config.Category.html#module-ntnx_prism_py_client.models.prism.v4.config.Category
                new_category = ntnx_prism_py_client.models.prism.v4.config.Category.Category(
                    key=category["name"],
                    value=category["value"],
                    description=category["description"],
                    type=ntnx_prism_py_client.models.prism.v4.config.CategoryType.CategoryType.USER,
                )
                # create the new category
                create_category = prism_instance.create_category(
                    async_req=False, body=new_category
                )
                # get the ext_id for the new category
                category_ext_id = create_category.data.ext_id
                print(
                    f"New category has been created with ext_id \
{category_ext_id}.\n"
                )
        except AttributeError as ex:
            print(
                "Attribute error while creating new category instance. \
Details:"
            )
            print(ex)
            sys.exit()
        except KeyError:
            print(
                f"KeyError: {category_specs} does not contain the required \
keys. Check the format then try again."
            )
            sys.exit()
        except PrismException as ex:
            print("Category cannot be created.  Details:")
            print(ex)
    else:
        print("Category creation cancelled.")

    sys.exit()


if __name__ == "__main__":
    main()
