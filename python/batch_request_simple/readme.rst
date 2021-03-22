Python Code Samples - batch_request_simple.py
#############################################

This readme file is specifically for the **batch_request_simple.py** Python code sample.

The setup instructions are the same as all other python code samples in this repository.  This file is provided as additional/supplemental information for this specific code sample.

Please see the `main <https://github.com/nutanixdev/code-samples/tree/master/python>`_ page for general instructions.

**Usage instructions are shown at the bottom of this page.**

Code Sample Details
...................

A quick intro, first.  The **batch_request_simple.py** code sample shows a basic demo of REST API batch requests with Python 3.  The expectation is that users wanting to run several request at the same time.  For example:

- Multiple VMs needing the same change
- Sequential requests that relate to one another (although they don't need to, at all)

**batch_request_simple.py** has been provided for demo purposes and should only be used with the following provisions in mind:

- A single batch should not contain no more than 60 individual requests
- Additional exception handling should be added before using this in production

JSON Parameters file
....................

A sample parameters file has been provided with this script.  It contains variables for:

- Prism Central IP address
- Prism Central username
- The POST payload to be used with the **batch** request.  In a 'real world' situation you could update this sample payload to carry out the requests you require.

Usage
-----

It is strongly recommended to read the more detailed explanation of using batch requests as been outlined here: `Batch Brewing – Multiple Requests with the Nutanix APIs <https://www.nutanix.dev/2019/11/19/batch-brewing-multiple-requests-with-the-nutanix-apis/>`_.

.. code-block:: bash

   usage: batch_request_simple.py [-h] json

   positional arguments:
     json        JSON file containing query parameters

   optional arguments:
     -h, --help  show this help message and exit

Example:

.. code-block:: bash

   /usr/bin/python3.8 ./batch_request_simple.py batch_request_simple.json
