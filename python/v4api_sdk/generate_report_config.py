"""
Use the Nutanix v4 API SDKs to demonstrate AI Ops report configuration creation
Requires Prism Central 2024.3 or later and AOS 7.0 or later
"""

import urllib3
import uuid

from ntnx_opsmgmt_py_client.rest import ApiException as ReportingException
# there's no need to import the namespace's configuration and client modules
# as that is all handled by the tme.ApiClient module

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

# utilities functions and classes e.g. environment management
from tme.utils import Utils

# functions and classes for Prism Central connection management
from tme.apiclient import ApiClient


def main():
    """
    suppress warnings about insecure connections
    please consider the security implications before
    doing this in a production environment
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    utils = Utils()
    config = utils.get_environment()

    default_start = "2025-01-01T00:00:00Z"
    default_end = "2025-01-02T00:00:00Z"

    # prompt for report start and end time
    # include sensible defaults
    print("You will now be prompted for the report start and end times.")
    print("Press enter at each prompt if you want to accept the defaults.")
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
        # setup the instance of our ApiClient class
        # this handles all Prism Central connections and provides
        # access to the chosen namespace's APIs, when required
        # this demo requires the OpsMgmt namespace i.e. ntnx_opsmgmt_py_client
        reporting_client = ApiClient(config=config, sdk_module="ntnx_opsmgmt_py_client")

        # with the client setup, specify the Nutanix v4 API we want to use
        # this section requires use of the ReportConfigApi
        reporting_instance = reporting_client.imported_module.api.ReportConfigApi(
            api_client=reporting_client.api_client
        )

        input(
            "\nThis demo uses the Nutanix v4 API `opsmgmt` namespace's \
reporting APIs to create an AIOps report configuration. \
The new report configuration can be used to run a manual or scheduled \
report. You will now be prompted for some report-specific details.\n\nPress ENTER to continue."
        )

        # get a list of existing report configurations
        print("Building list of existing report configurations ...")

        config_list = reporting_instance.list_report_configs(async_req=False)

        if config_list.data:
            print(f"{len(config_list.data)} report configurations found.")
        else:
            print("No report configurations found.")

        recipient_name = input("Enter the report recipient name: ")
        recipient_email = input("Enter the report recipient email address: ")

        # dates must be ISO-8601 compliant
        report_config_name = f"sdk_chrisr_config_{str(uuid.uuid4())}"

        print("Report configuration will be as follows:")
        print(f"   Configuration name: {report_config_name}")
        print(f"   Start time: {start_time}")
        print(f"   End time: {end_time}")
        print("   Report interval: Yearly")

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

        create_new_config = reporting_instance.create_report_config(
            async_req=False, body=new_config
        )

        reporting_ext_id = create_new_config.data.ext_id
        utils.monitor_task(
            task_ext_id=reporting_ext_id,
            prefix="",
            task_name="Report config creation",
            pc_ip=config.pc_ip,
            username=config.pc_username,
            password=config.pc_password,
            poll_timeout=1,
        )

        print("Report config created.")

    except ReportingException as reporting_exception:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Check your username and/or password, then try again.  \
Exception details: {reporting_exception}"
        )


if __name__ == "__main__":
    main()
