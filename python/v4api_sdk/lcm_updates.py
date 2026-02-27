"""
Use the Nutanix v4 API SDKs to gather a list of upgradeable LCM entities,
then generate an LCM update plan
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import getpass
import argparse
import time
import sys
from pprint import pprint
import urllib3
from timeit import default_timer as timer

# only the ntnx_lifecycle_py_client namespace is required for this code sample
import ntnx_lifecycle_py_client
from ntnx_lifecycle_py_client import ApiClient as LCMClient
from ntnx_lifecycle_py_client import Configuration as LCMConfiguration
from ntnx_lifecycle_py_client.rest import ApiException as LCMException

# required for building the list of LCM components that can be updated
from ntnx_lifecycle_py_client.models.lifecycle.v4.common.PrechecksSpec import PrechecksSpec
from ntnx_lifecycle_py_client.models.lifecycle.v4.resources.RecommendationSpec import RecommendationSpec
from ntnx_lifecycle_py_client.models.lifecycle.v4.resources.NotificationsSpec import NotificationsSpec
from ntnx_lifecycle_py_client.models.lifecycle.v4.common.EntityUpdateSpec import EntityUpdateSpec
from ntnx_lifecycle_py_client.models.lifecycle.v4.common.EntityType import EntityType
from ntnx_lifecycle_py_client.models.lifecycle.v4.common.UpgradeSpec import UpgradeSpec
from ntnx_lifecycle_py_client.models.lifecycle.v4.common.SystemAutoMgmtFlag import SystemAutoMgmtFlag
from ntnx_lifecycle_py_client.api import InventoryApi
from ntnx_lifecycle_py_client.api import EntitiesApi
from ntnx_lifecycle_py_client.api import RecommendationsApi
from ntnx_lifecycle_py_client.api import NotificationsApi
from ntnx_lifecycle_py_client.api import UpgradesApi

# required for getting cluster details
import ntnx_clustermgmt_py_client
from ntnx_clustermgmt_py_client import Configuration as ClusterConfiguration
from ntnx_clustermgmt_py_client import ApiClient as ClusterClient
from ntnx_clustermgmt_py_client.rest import ApiException as ClusterException
from ntnx_clustermgmt_py_client.api import ClustersApi

# required for getting task details
import ntnx_prism_py_client
from ntnx_prism_py_client import Configuration as PrismConfiguration
from ntnx_prism_py_client import ApiClient as PrismClient
from ntnx_prism_py_client.rest import ApiException as PrismException
from ntnx_prism_py_client.api import TasksApi

# small library that manages commonly-used tasks across these code samples
from tme.utils import Utils
from tme.apiclient import ApiClient


def main():
    """
    suppress warnings about insecure connections
    consider the security implications before
    doing this in a production environment
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    utils = Utils()
    config = utils.get_environment()

    try:

        # build the configurations
        lcm_config = LCMConfiguration()
        cluster_config = ClusterConfiguration()
        prism_config = PrismConfiguration()

        for configuration in [lcm_config, cluster_config, prism_config]:
            configuration.host = config.pc_ip
            configuration.username = config.pc_username
            configuration.password = config.pc_password
            configuration.verify_ssl = False

        # create utils instance for re-use later
        utils = Utils(pc_ip=config.pc_ip, username=config.pc_username, password=config.pc_password)

        # build the API clients
        lcm_client = LCMClient(configuration=lcm_config)
        cluster_client = ClusterClient(configuration=cluster_config)
        prism_client = PrismClient(configuration=prism_config)

        for client in [lcm_client, cluster_client, prism_client]:
            client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )

        # list clusters
        cluster_instance = ClustersApi(api_client=cluster_client)
        print("Getting cluster list ...")

        # option 1 - filter by specific cluster name
        # cluster_list = cluster_instance.list_clusters(async_req=False, _filter="name eq 'Dev'")

        # option 2 - filter by Prism Central clusters only
        cluster_list = cluster_instance.list_clusters(async_req=False, _filter="config/clusterFunction/any(a:a eq Clustermgmt.Config.ClusterFunctionRef'PRISM_CENTRAL')")

        # get the cluster extid
        # some LCM APIs support the user of a specific cluster ID
        cluster_extid = cluster_list.data[0].ext_id
        cluster_name = cluster_list.data[0].name

        # the confirm function simply asks for a yes/NO confirmation before
        # continuing with the specified action
        run_inventory = utils.confirm(
            "Run LCM Inventory?  This can take some time, depending on \
environment configuration."
        )
        if run_inventory:
            # start an LCM inventory
            lcm_instance = InventoryApi(api_client=lcm_client)
            print("Starting LCM inventory ...")
            inventory = lcm_instance.perform_inventory(async_req=False, X_Cluster_id=cluster_extid)

            # grab the unique identifier for the LCM inventory task
            inventory_task_ext_id = inventory.data.ext_id
            inventory_duration = utils.monitor_task(
                task_ext_id=inventory_task_ext_id,
                task_name="Inventory",
                pc_ip=utils.prism_config.host,
                username=utils.prism_config.username,
                password=utils.prism_config.password,
            )
            print(f"Inventory duration: {inventory_duration}.")
        else:
            print("LCM Inventory skipped.")


        # gather a list of supported entities
        # this will be used to show human-readable update info shortly
        lcm_instance = EntitiesApi(api_client=lcm_client)
        print("Getting Supported Entity list ...")
        entities = lcm_instance.list_entities(async_req=False, X_Cluster_Id=cluster_extid)

        """
        gather LCM update recommendations
        """
        lcm_instance = RecommendationsApi(api_client=lcm_client)
        print("Computing LCM Recommendations ...")
        rec_spec = RecommendationSpec()

        print("Checking for SOFTWARE and FIRMWARE")
        rec_spec.recommendation_spec = [
                EntityType.SOFTWARE,
                EntityType.FIRMWARE
        ]

        # specify that this script should only look for available software updates
        recommendations = lcm_instance.compute_recommendations(
            async_req=False, body=rec_spec, X_Cluster_Id=cluster_extid
        )

        recs_task_id = recommendations.data.ext_id
        prism_instance = TasksApi(api_client=prism_client)
        print("Getting Recommendations task ...")
        recs_task = prism_instance.get_task_by_id(recs_task_id)
        while recs_task.data.status == "RUNNING":
            print("Checking Recommendation task status every 5 seconds ...")
            recs_task = prism_instance.get_task_by_id(recs_task_id)
            time.sleep(5)
        completion_value = recs_task.data.completion_details[0].value

        # get recommendation details
        lcm_instance = RecommendationsApi(api_client=lcm_client)
        recommendation = lcm_instance.get_recommendation_by_id(completion_value)

        # make sure there are updates available before continuing
        if recommendation.data.entity_update_specs:
            entity_details = []
            lcm_instance = ntnx_lifecycle_py_client.api.EntitiesApi(api_client=lcm_client)
            for rec in recommendation.data.entity_update_specs:
                entity = lcm_instance.get_entity_by_id(rec.entity_uuid)
                entity_details.append({"entity_uuid": entity.data.ext_id, "entity_model": entity.data.entity_model, "to_version": entity.data.target_version})
            print(f"{len(entity_details)} components can be updated.")
        else:
            print("No updates available, skipping LCM Update planning.")
            sys.exit()

        # compute notifications
        print("Computing LCM Notifications ...")
        lcm_instance = NotificationsApi(api_client=lcm_client)
        notifications_spec = NotificationsSpec()
        notifications_spec.notifications_spec = recommendation.data.entity_update_specs
        notifications = lcm_instance.compute_notifications(async_req=False, X_Cluster_Id=cluster_extid, body=notifications_spec)

        notifications_task_id = notifications.data.ext_id
        print("Getting Notifications task ...")
        notifications_task = prism_instance.get_task_by_id(notifications_task_id)
        while notifications_task.data.status == "RUNNING":
            print("Checking Notification task status every 5 seconds ...")
            notifications_task = prism_instance.get_task_by_id(notifications_task_id)
            time.sleep(5)
        completion_value = notifications_task.data.completion_details[0].value

        # get notification details
        notification = lcm_instance.get_notification_by_id(completion_value)

        if notification.data.notifications:
            print(f"There are {len(notification.data.notifications)} notifications available:\n")
            for notification_details in notification.data.notifications:
                print(f"    Class: {notification_details.entity_class}")
                print(f"    Model: {notification_details.entity_model}")
                print(f"    Message: {notification_details.details[0].message}\n")

        if utils.confirm("Continue with upgrades?  DO NOT use this demo script in production without modification appropriate for your environment!"):
            print("Upgrading ...")
        else:
            print("Upgrades cancelled ...")
            sys.exit()

        print("Building Upgrade spec ...")
        upgrade_spec = UpgradeSpec()
        upgrade_spec.skipped_precheck_flags = [
            # power off user VMs, if required
            SystemAutoMgmtFlag.POWER_OFF_UVMS,
            # migrate powered off user VMs to other hosts, if required
            SystemAutoMgmtFlag.MIGRATE_POWERED_OFF_UVMS
        ]
        upgrade_spec.entity_update_specs = recommendation.data.entity_update_specs
        lcm_instance = UpgradesApi(api_client=lcm_client)
        # start the upgrades
        # note dry run is only supported in specific circumstances (usually not AHV, with some exceptions)
        upgrades = lcm_instance.perform_upgrade(async_req=False, X_Cluster_Id=cluster_extid, body=upgrade_spec)

        upgrades_task_id = upgrades.data.ext_id
        print("Getting Upgrades task ...")
        upgrades_task = prism_instance.get_task_by_id(upgrades_task_id)
        while upgrades_task.data.status == "RUNNING":
            print("Checking Upgrades task status every 5 seconds ...")
            upgrades_task = prism_instance.get_task_by_id(upgrades_task_id)
            time.sleep(5)

        print("Done!")

    except (LCMException, ClusterException) as lcm_exception:
        print(
            f"Unable to complete the requested action.  See below for \
additional details.  \
Exception details: {lcm_exception}"
        )

if __name__ == "__main__":
    main()
