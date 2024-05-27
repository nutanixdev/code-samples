import sys
import urllib3
import uuid
import os
from requests.auth import HTTPBasicAuth
import json
from dataclasses import dataclass


import ntnx_lifecycle_py_client
from ntnx_lifecycle_py_client import ApiClient as LCMClient
from ntnx_lifecycle_py_client import Configuration as LCMConfiguration

from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client import Configuration as PrismConfiguration

import ntnx_clustermgmt_py_client
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient
from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration

import ntnx_vmm_py_client
from ntnx_vmm_py_client import ApiClient as VMMClient
from ntnx_vmm_py_client import Configuration as VMMConfiguration

from ntnx_microseg_py_client import ApiClient as MicrosegClient
from ntnx_microseg_py_client import Configuration as MicrosegConfiguration

from ntnx_lifecycle_py_client.models.lifecycle.v4.resources.RecommendationSpec import (
    RecommendationSpec,
)


@dataclass
class Config:
    """
    dataclass to hold configuration for each script run
    nice and modular
    """

    pc_ip: str
    pc_username: str
    pc_password: str
    cluster_name: str


def main():
    # load the configuration
    try:
        if os.path.exists("./startup.json"):
            with open("./startup.json", "r", encoding="utf-8") as config_file:
                config_json = json.loads(config_file.read())
        else:
            print("Configuration file not found.")
    except json.decoder.JSONDecodeError as config_error:
        print(f"Unable to load configuration: {config_error}")

    # assign variables based on config loaded from JSON file
    user_config = Config(
        pc_ip=config_json["pc_ip"],
        pc_username=config_json["pc_username"],
        pc_password=config_json["pc_password"],
        cluster_name=config_json["cluster_name"],
    )

    # create HTTPBasicAuth instance, for use cases requiring basic auth vs SDK auth
    prism_central_auth = HTTPBasicAuth(user_config.pc_username, user_config.pc_password)

    # set to true if you have a connection to Prism Central
    live = True

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    lcm_config = LCMConfiguration()
    prism_config = PrismConfiguration()
    vmm_config = VMMConfiguration()
    cluster_config = ClusterConfiguration()
    microseg_config = MicrosegConfiguration()

    for config in [
        lcm_config,
        prism_config,
        vmm_config,
        cluster_config,
        microseg_config,
    ]:
        config.host = user_config.pc_ip
        config.username = user_config.pc_username
        config.password = user_config.pc_password
        config.verify_ssl = False

    lcm_client = LCMClient(configuration=lcm_config)
    prism_client = PrismClient(configuration=prism_config)
    vmm_client = VMMClient(configuration=vmm_config)
    cluster_client = ClusterClient(configuration=cluster_config)
    microseg_client = MicrosegClient(configuration=microseg_config)

    for client in [
        lcm_client,
        prism_client,
        vmm_client,
        cluster_client,
        microseg_client,
    ]:
        client.add_default_header(
            header_name="Accept-Encoding", header_value="gzip, deflate, br"
        )

    rec_spec = RecommendationSpec()
    rec_spec.entity_types = ["software"]

    lcm_instance = ntnx_lifecycle_py_client.api.RecommendationsApi(
        api_client=lcm_client
    )

    cluster_instance = ntnx_clustermgmt_py_client.api.ClustersApi(
        api_client=cluster_client
    )
    if live:
        try:
            cluster_list = cluster_instance.list_clusters(async_req=False)
            cluster = [
                x for x in cluster_list.data if x.name == user_config.cluster_name
            ]
            cluster_extid = cluster[0].ext_id
        except ntnx_clustermgmt_py_client.rest.ApiException as ex:
            print(type(ex))
            sys.exit()
    else:
        # this will mean actions requiring a cluster extid e.g. image creation
        # will fail
        cluster_extid = ""
        print("\n*** Warning: live is set to False.  Expect errors ...\n")

    unique_id = uuid.uuid1()

    new_image = ntnx_vmm_py_client.models.vmm.v4.content.Image.Image()
    new_image.name = f"image_{unique_id}"
    new_image.desc = "no desc"
    new_image.type = "DISK_IMAGE"
    image_source = ntnx_vmm_py_client.models.vmm.v4.content.UrlSource.UrlSource()
    image_source.url = "https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud-2003.qcow2"
    image_source.allow_insecure = False
    new_image.source = image_source
    image_cluster = (
        ntnx_vmm_py_client.models.vmm.v4.ahv.config.ClusterReference.ClusterReference()
    )
    image_cluster.ext_id = cluster_extid
    new_image.initial_cluster_locations = [image_cluster]

    vmm_instance = ntnx_vmm_py_client.api.ImagesApi(api_client=vmm_client)

    # image_create = vmm_instance.create_image(async_req=False, body=new_image)


if __name__ == "__main__":
    main()
