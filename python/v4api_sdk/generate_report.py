"""
Use the Nutanix v4 API SDKs to demonstrate AI Ops report creation
Requires Prism Central 2024.3 or later and AOS 6.9 or later
"""

import urllib3
import uuid
import sys
from pprint import pprint

from ntnx_opsmgmt_py_client.rest import ApiException as ReportingException
from ntnx_opsmgmt_py_client import Report
from ntnx_opsmgmt_py_client.models.opsmgmt.v4.config.ReportFormat import ReportFormat
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
reporting APIs to create an AIOps report from an existing report configuration. \
You will now be prompted for some report-specific details.\n\nPress ENTER to continue."
        )

        # get a list of existing report configurations
        print("Building list of existing user-defined report configurations ...")

        # config_list = reporting_instance.list_report_configs(
        #     async_req=False, _filter="isSystemDefined eq null", _limit=100
        # )

        config_list = reporting_instance.list_report_configs(async_req=False)

        if config_list.data:
            print(f"{len(config_list.data)} report configurations found.")
        else:
            print("No report configurations found. Exiting ...")
            sys.exit()

        recipient_name = input("Enter the report recipient name: ")
        recipient_email = input("Enter the report recipient email address: ")

        user_configs = []
        for report_config in config_list.data:
            user_configs.append(
                {"name": report_config.name, "ext_id": report_config.ext_id}
            )
        pprint(user_configs)
        config_ext_id = input(
            "Enter the ext_id of the report configuration to use for this report: "
        )

        report_name = f"sdk_new_report_{str(uuid.uuid4())}"

        print("Report configuration will be as follows:")
        print(f"   Report name: {report_name}")
        print(f"   Config ext_id: {config_ext_id}")
        print(f"   Start time: {start_time}")
        print(f"   End time: {end_time}")
        print("   Persistent: No")
        print(f"   Recipient: {recipient_name}, {recipient_email}")
        print("   Report format: PDF")

        PDF = ReportFormat.PDF

        new_report = Report(
            name=f"{report_name}",
            description="report configuration created from v4 python SDK",
            config_ext_id=config_ext_id,
            start_time=start_time,
            end_time=end_time,
            is_persistant=False,
            recipients=[
                Recipient(email_address=recipient_email, recipient_name=recipient_name)
            ],
            recipient_formats=[PDF],
        )

        print("Submitting report creation request ...")

        reporting_instance = reporting_client.imported_module.api.ReportsApi(
            api_client=reporting_client.api_client
        )

        create_new_report = reporting_instance.create_report(
            async_req=False, body=new_report
        )

        reporting_ext_id = create_new_report.data.ext_id
        utils.monitor_task(
            task_ext_id=reporting_ext_id,
            prefix="",
            task_name="Report config creation",
            pc_ip=config.pc_ip,
            username=config.pc_username,
            password=config.pc_password,
            poll_timeout=1,
        )

        print("Report generated.")

    except ReportingException as reporting_exception:
        print(
            f"Unable to authenticate using the supplied credentials.  \
Check your username and/or password, then try again.  \
Exception details: {reporting_exception}"
        )


if __name__ == "__main__":
    main()
