# Categories v4 Workflow Sample Scripts

Code sample to demonstrate use of the Categories v4 APIs via Python client.

Requires Prism Central 2024.3 or later and AOS 6.8 or later.

## Usage

- Create and activate a Python virtual environment:

  ```
  python -m venv venv
  . venv/bin/activate
  ```

- Install required packages:

  ```
  pip install -r requirements.txt
  ```
- Update the following variables in the script:

  ```
  CLUSTER_NAME = "<CLUSTER_NAME>"
  ```
  Note: For updating owner_uuid of a category, provide the user's UUID in the script and it must be correct.
- Run script:

  ```
  python categories_v4_workflow.py --pc_ip <PRISM_CENTRAL_IP> --username <USERNAME>
  ```

  Note: User will be prompted for password

