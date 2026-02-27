"""
Use the Nutanix v4 API SDKs to demonstrate AI Ops report configuration creation
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import uuid
import urllib3
from rich import print

import ntnx_opsmgmt_py_client
from ntnx_opsmgmt_py_client import Configuration as OpsMgmtConfiguration
from ntnx_opsmgmt_py_client import ApiClient as OpsMgmtClient
from ntnx_opsmgmt_py_client.rest import ApiException as ReportingException

# reporting-specific libraries
from ntnx_opsmgmt_py_client import ReportConfig, ReportSchedule
from ntnx_opsmgmt_py_client import EntityType
from ntnx_opsmgmt_py_client import (
    Widget,
    WidgetType,
    WidgetConfig,
    WidgetSize,
    WidgetField,
)
from ntnx_opsmgmt_py_client import ScheduleInterval
from ntnx_opsmgmt_py_client import Row
from ntnx_opsmgmt_py_client import Section
from ntnx_opsmgmt_py_client import RepeatCriteria, DataCriteria
from ntnx_opsmgmt_py_client import AggregateFunction
from ntnx_opsmgmt_py_client.models.opsmgmt.v4.config.ReportFormat import ReportFormat
from ntnx_opsmgmt_py_client.models.opsmgmt.v4.config.SortOrder import SortOrder
from ntnx_opsmgmt_py_client.models.opsmgmt.v4.config.NotificationPolicy import (
    NotificationPolicy,
)
from ntnx_opsmgmt_py_client.models.opsmgmt.v4.config.Recipient import Recipient

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

    default_start = "2025-01-01T00:00:00Z"
    default_end = "2025-01-02T00:00:00Z"

    # prompt for report start and end time
    # include sensible defaults
    print("You will now be prompted for the report start and end times.")
    print("Press enter at each prompt to accept the default values.")
    print(f"Default start time: {default_start}")
    print(f"Default end time: {default_end}")

    start_time = input("Enter the report start time in ISO-8601 format: ")
    if not start_time:
        start_time = default_start
        print("Default start time used ...")
    end_time = input("Enter the report end time in ISO-8601 format: ")
    if not end_time:
        end_time = default_end
        print("Default end time used ...")

    try:
        
        opsmgmt_config = OpsMgmtConfiguration()

        for config in [
            opsmgmt_config,
        ]:
            config.host = script_config.pc_ip
            config.username = script_config.pc_username
            config.password = script_config.pc_password
            config.verify_ssl = False

        opsmgmt_client = OpsMgmtClient(configuration=opsmgmt_config)

        for client in [
            opsmgmt_client,
        ]:
            client.add_default_header(
                header_name="Accept-Encoding", header_value="gzip, deflate, br"
            )

        opsmgmt_instance = ntnx_opsmgmt_py_client.api.ReportConfigApi(api_client=opsmgmt_client)

        print("This demo uses the Nutanix v4 API `opsmgmt` \
namespace's reporting APIs to create an \
AIOps report configuration. The new report \
configuration can be used to run a manual \
or scheduled report. You will now be \
prompted for some report-specific details.")

        # get a list of existing report configurations
        print("Building list of existing report configurations ...")

        config_list = opsmgmt_instance.list_report_configs(async_req=False)

        if config_list.data:
            print(f"{len(config_list.data)} report configurations found, including system and built-in configurations.")
        else:
            print("No report configurations found.")

        recipient_name = input("Enter the report recipient name: ")
        recipient_email = input("Enter the report recipient email address: ")

        # dates must be ISO-8601 compliant
        report_config_name = f"sdk_report_config_{str(uuid.uuid4())}"

        print("Report configuration will be as follows:")
        print(f"   Configuration name: {report_config_name}")
        print(f"   Start time: {start_time}")
        print(f"   End time: {end_time}")
        print("   Report interval: Yearly\n")

        # report format: PDF or CSV
        PDF = ReportFormat.PDF
        # DAILY, WEEKLY, MONTHLY, YEARLY
        YEARLY = ScheduleInterval.YEARLY

        new_config = ReportConfig(
            name=f"{report_config_name}",
            description="report configuration created from v4 python SDK",
            schedule=ReportSchedule(
                # internal as above i.e. daily/weekly/monthly/yearly
                schedule_interval=YEARLY,
                # how often the report should run
                frequency=1,
                # required: when the schedule should end
                start_time=start_time,
                # optional: the last time the report should run
                end_time=end_time,
            ),
            sections=[
                Section(
                    name="First Section",
                    description="This is the first section in the report",
                    rows=[
                        Row(
                            widgets=[
                                Widget(
                                    widget_info=WidgetConfig(
                                        fields=[
                                            WidgetField(
                                                label="CPU usage",
                                                name="hypervisor_cpu_usage_ppm",
                                                aggregate_function=AggregateFunction.AVG,
                                            )
                                        ],
                                        entity_type=EntityType.VM,
                                        heading="VM CPU Usage (%)",
                                        size=WidgetSize.FULLSPAN,
                                        type=WidgetType.LINE_CHART,
                                        data_criteria=DataCriteria(
                                            sort_column="hypervisor_cpu_usage_ppm",
                                            sort_order=SortOrder.ASCENDING,
                                        ),
                                    )
                                )
                            ]
                        )
                    ],
                    repeat_criteria=RepeatCriteria(entity_type=EntityType.VM),
                )
            ],
            supported_formats=[PDF],
            timezone="UTC",
            notification_policy=NotificationPolicy(
                recipient_formats=[PDF],
                email_body="Nutanix Prism Central Report; this report \
was generated from a report created using the Nutanix \
v4 Python SDK.",
                email_subject="Nutanix Prism Central Report",
                recipients=[
                    Recipient(
                        email_address=f"{recipient_email}",
                        recipient_name=f"{recipient_name}",
                    )
                ],
            ),
            default_section_entity_type=EntityType.VM,
        )

        print("Submitting report config creation request ...")

        create_new_config = opsmgmt_instance.create_report_config(
            async_req=False, body=new_config
        )

        reporting_ext_id = create_new_config.data.ext_id
        utils.monitor_task(
            task_ext_id=reporting_ext_id,
            prefix="",
            task_name="Report config creation",
            pc_ip=script_config.pc_ip,
            username=script_config.pc_username,
            password=script_config.pc_password,
        )

        print(f"Report config named {report_config_name} created.\n")

    except ReportingException as reporting_exception:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Check your username and/or password, then try again.  \
Exception details: {reporting_exception}"
        )


if __name__ == "__main__":
    main()