"""
Use the Nutanix v4 API SDKs to create a Prism Central image
"""

import getpass
import argparse
import sys
import uuid
from pprint import pprint
import urllib3

import ntnx_vmm_py_client
from ntnx_vmm_py_client import ApiClient as VMMClient
from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client.rest import ApiException as VMMException

import ntnx_clustermgmt_py_client
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient
from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration

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
            prompt="Please enter your Prism Central password: ",
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
                            Please enter a password or Ctrl-C/Ctrl-D to exit."
                            )
            cluster_password = getpass.getpass(
                    prompt="Please enter your Prism Central password: ", stream=None
                    )

    try:
        # create utils instance for re-use later
        utils = Utils(pc_ip=pc_ip, username=username, password=cluster_password)

        # before creating the image we need to find out which cluster
        # the image will live on
        # for this demo, we will get the ext_id of the first non-PC
        # cluster visible in this PC instance
        cluster_config = ClusterConfiguration()
        cluster_config.host = pc_ip
        cluster_config.username = username
        cluster_config.password = cluster_password
        cluster_config.max_retry_attempts = 1
        cluster_config.backoff_factor = 3
        cluster_config.verify_ssl = False
        api_client = ClusterClient(configuration=cluster_config)
        api_instance = ntnx_clustermgmt_py_client.api.ClustersApi(api_client=api_client)
        print("Retrieving cluster list ...")
        cluster_list = api_instance.list_clusters(async_req=False)

        # do some verification and make sure the user creates the image on the correct cluster
        found_clusters = []

        for cluster in cluster_list.data:
            if not cluster.name == "Unnamed":
                found_clusters.append({"name": cluster.name, "ext_id": cluster.ext_id})
        print(
                f"The following clusters ({len(cluster_list.data)-1}) were found, not including Prism Central."
                )
        print(
                "Note: By default Prism Central clusters appear as 'Unnamed'.  Clusters matching this name have \
                        not been included in this list."
                        )
        pprint(found_clusters)
        expected_cluster_name = input(
                "\nPlease enter the name of the destination cluster: "
                ).lower()

        matches = [
                x
                for x in found_clusters
                if x["name"].lower() == expected_cluster_name.lower()
                ]
        if not matches:
            print(
                    f"No cluster found matching the name {expected_cluster_name}.  Exiting."
                    )
            sys.exit()

        # get the cluster ext_id
        cluster_ext_id = matches[0]["ext_id"]

        # setup the configuration parameters
        vmm_config = VMMConfiguration()
        vmm_config.host = pc_ip
        vmm_config.username = username
        vmm_config.password = cluster_password
        # known issue in pc.2022.6 that ignores this setting
        vmm_config.max_retry_attempts = 1
        vmm_config.backoff_factor = 3
        vmm_config.verify_ssl = False
        api_client = VMMClient(configuration=vmm_config)
        api_client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
                )
        api_instance = ntnx_vmm_py_client.api.ImagesApi(api_client=api_client)

        # generate unique ID to ensure image names are always different
        unique_id = uuid.uuid1()

        # setup new image properties
        new_image = ntnx_vmm_py_client.models.vmm.v4.content.Image.Image()
        new_image.name = f"rocky_linux_9_cloud_{unique_id}"
        new_image.desc = "Rocky Linux 9 Cloud Image"
        new_image.type = "DISK_IMAGE"
        image_source = ntnx_vmm_py_client.models.vmm.v4.content.UrlSource.UrlSource()
        image_source.url = "https://dl.rockylinux.org/pub/rocky/9/images/x86_64/Rocky-9-GenericCloud-Base.latest.x86_64.qcow2" 
        image_source.allow_insecure = False
        new_image.source = image_source
        image_cluster = ntnx_vmm_py_client.models.vmm.v4.ahv.config.ClusterReference.ClusterReference()
        image_cluster.ext_id = cluster_ext_id
        new_image.initial_cluster_locations = [image_cluster]

        confirm_create = utils.confirm("Create image?")
        if confirm_create:
            print(f"Creating image with name {new_image.name} ...")
            image_create = api_instance.create_image(async_req=False, body=new_image)

            # grab the ext ID of the create image task
            # this method is a little cumbersome but allows task IDs from
            # different endpoints and APIs to be used with the
            # monitor_task function
            create_ext_id = image_create.data.ext_id
            utils.monitor_task(
                    task_ext_id=create_ext_id,
                    task_name="Create image",
                    pc_ip=pc_ip,
                    username=username,
                    password=cluster_password,
                    poll_timeout=poll_timeout,
                    )
            task = utils.get_task(create_ext_id)
            print(f"Image created with ext_id {task.data.entities_affected[0].ext_id}")
        else:
            print("Image creation cancelled.")

    except VMMException as vmm_exception:
        print(
                f"Unable to authenticate using the supplied credentials.  \
                        Please check your username and/or password, then try again.  \
                        Exception details: {vmm_exception}"
                        )


if __name__ == "__main__":
    main()
