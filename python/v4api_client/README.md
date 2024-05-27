# Nutanix v4 API Sample Scripts

Code sample to demonstrate use of the new Nutanix v4 APIs via Python client.

Requires Prism Central 2024.1 or later and AOS 6.8 or later.

## Recommendations

These demos are specifically for environments where the use of Nutanix v4 SDKs is not possible.  Where possible, it is recommended to use and implement the Nutanix v4 SDKs.

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
  python list_images_client.py <prism_central_ip> <username>
  ```

  Note: User will be prompted for password

