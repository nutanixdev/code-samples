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

- Run script:

  ```
  python categories_v4_workflow.py --pc_ip <PRISM_CENTRAL_IP> --username <USERNAME>
  ```

**Note:**

1. **Password for the provided username**:
   You will be prompted to enter the password associated with the specified username.

2. **Cluster name**:
   Ensure you provide the correct Cluster name. This will be used to create the VM, and it must be accurate to avoid any configuration errors.

3. **New owner extId (UUID)**:
   Provide the `IAM user extId (UUID)` to update the `owner_uuid` of the category. The `extId` must be correct for the script to execute successfully.
