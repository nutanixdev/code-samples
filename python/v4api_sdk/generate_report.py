"""
Use the Nutanix v4 API SDKs to demonstrate AI Ops report creation
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
"""

import uuid
import sys
from pprint import pprint
import urllib3
from rich import print

import ntnx_opsmgmt_py_client
from ntnx_opsmgmt_py_client import Configuration as OpsMgmtConfiguration
from ntnx_opsmgmt_py_client import ApiClient as OpsMgmtClient
from ntnx_opsmgmt_py_client.rest import ApiException as ReportingException
from ntnx_opsmgmt_py_client import Report
from ntnx_opsmgmt_py_client.models.opsmgmt.v4.config.ReportFormat import ReportFormat
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

        print("This demo uses the Nutanix v4 API `opsmgmt` namespace's \
reporting APIs to create an AIOps report from an existing \
report configuration. You will now be prompted for some \
report-specific details.")

        # get a list of existing report configurations
        print("Building list of existing user-defined report configurations ...")

        config_list = opsmgmt_instance.list_report_configs(
            async_req=False, _filter="isSystemDefined eq null", _limit=100
        )

        if config_list.data:
            print(f"{len(config_list.data)} user-defined report configurations found.")
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
        print("Available report configurations:")
        pprint(user_configs)
        config_ext_id = input("Enter the ext_id of the report configuration to use for this report: ")

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

        opsmgmt_instance = ntnx_opsmgmt_py_client.api.ReportsApi(api_client=opsmgmt_client)

        create_new_report = opsmgmt_instance.create_report(
            async_req=False, body=new_report
        )

        reporting_ext_id = create_new_report.data.ext_id
        utils.monitor_task(
            task_ext_id=reporting_ext_id,
            prefix="",
            task_name="Report config creation",
            pc_ip=script_config.pc_ip,
            username=script_config.pc_username,
            password=script_config.pc_password,
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
