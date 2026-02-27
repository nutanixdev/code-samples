# Nutanix Code Samples - Nutanix v4 REST APIs with Python requests

A collection of code samples demonstrating use of the Nutanix v4 REST APIs with Python `requests`.

Note: These code samples are specific to Python `requests` and do not demonstrate use of the Nutanix v4 Python SDK.  For Nutanix v4 Python SDK code samples, see the **python/v4api_sdk** directory within this repository.

## Requirements

- Python >=3.9 (3.9 or later)
- The accompanying JSON files from this repository (instructions and usage provided below).
- A suitable Python editor, e.g. **Microsoft Visual Studio Code <https://code.visualstudio.com/>**_ for GUI editing.
- Access to a Nutanix Prism Central instance, running Nutanix Prism Central 7.5 or later

## Python Environment

In February 2026, this repository moved from `pip` to [`uv`](https://docs.astral.sh/uv/); ensure you have installed `uv` before using the Nutanix v4 Python SDK code samples.

From a user perspective, script dependencies are now managed through `pyproject.toml` instead of `requirements.txt.`. See the following usage notes for complete `uv` usage with this repository.

## Nutanix v4 Python SDK Code Sample Usage

- Clone this repository; this is critical as it ensures the accompanying `tme` module is available.
- Install dependencies using `uv`:

  ```
  uv sync
  ```

- Run the script; the example below uses the `list_images.py` script:

  ```
  uv run list_images.py <prism_central_ip> <prism_central_username>
  ```

- The script will prompt for your account password, then submit the request based on the script spec.

  ![Screenshot of `uv sync`](screenshot_uv_sync.png)

  ![Screenshot of running list_images.py](screenshot_script.png)

  ![Screenshot of running update_image_etag.py](screenshot_script2.png)