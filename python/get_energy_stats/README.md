# Get Energy Stats

## Create and activate Python virtual environment

This section explains how to create a Python virtual environment and install the required non-standard libraries using `pip`.

Setting Up the Python Virtual Environment
To ensure that your project dependencies are isolated from other projects and the system Python packages, it is recommended to use a virtual environment. Follow these steps to set up a virtual environment and install the required libraries:

1. Create a Virtual Environment

   - Open a terminal and navigate to your project directory:

     Create a virtual environment named venv:

     ```
     python3 -m venv .virtualenvpower
     ```

2. Activate the Virtual Environment

   On macOS and Linux:

   ```
   source .virtualenvpower/bin/activate
   ```

   On Windows:

   ```
   .virtualenvpower\Scripts\activate
   ```

## Install Script Dependencies

3. Install Required Libraries

   With the virtual environment activated, install the required non-standard libraries using pip. The libraries needed for this project are listed below:

   - requests
   - prettytable

   You can install these libraries by running the following command:

   ```
   pip install -r requirements.txt
   ```

   Alternatively, the latest versions of each library can be installed by running the following command:

   ```
   pip install requests prettytable
   ```

4. Verify Installation

   To verify that the libraries have been installed correctly, you can list the installed packages:

   ```
   pip list
   ```

   You should see `requests` and `prettytable` listed among the installed packages.

5. Deactivate the Virtual Environment

   Once you are done working in the virtual environment, you can deactivate it by running:

   ```
   deactivate
   ```

By following these steps, you will have a virtual environment set up with the necessary libraries installed, ensuring that your project dependencies are managed effectively.
