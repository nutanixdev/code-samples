import boto3
from botocore.exceptions import ClientError
from botocore.exceptions import ParamValidationError
import sys

session = boto3.session.Session()

# configuration for this connection
# in a "real" script, these values would probably not be hard-coded
configuration = {
    "endpoint_url": "[endpoint_url_here]",
    "access_key": "[access_key_here]",
    "secret_key": "[secret_key_here]",
    "buckets": {
        "web-assets",
        "form-submissions"
    }
}

# create our s3c session using the variables above
# note "use_ssl=False", as outlined in the accompanying article
s3c = session.client(
    aws_access_key_id=configuration["access_key"],
    aws_secret_access_key=configuration["secret_key"],
    endpoint_url=configuration["endpoint_url"],
    service_name="s3",
    use_ssl=False,
)

# setup our bucket lifecycle policy
# please use this carefully as these settings will need to be
# altered before use outside this demo environment
lifecycle_policy = {
    "Rules": [
        {
            "Expiration": {"Days": 10},
            "Filter": {"Prefix": "demo"},
            "Status": "Enabled",
            "ID": "ExpiryPolicy-10Days-ObjectPrefix-demo",
        },
        {
            "Expiration": {"Days": 30},
            "Filter": {"Prefix": "object"},
            "Status": "Enabled",
            "ID": "ExpiryPolicy-1Month-ObjectPrefix-object",
        }
    ]
}

# iterate over the bucket list, verify that each one does
# not already exist and, if not, attempt to create it
for bucket in configuration["buckets"]:
    pass

    # check if bucket exists
    try:
        s3c.head_bucket(Bucket=bucket)
        print(f"Bucket exists : {bucket}")
    except ClientError:
        print(f"Bucket {bucket} does not exist.  "
              + "Attempting to create bucket ...")
        try:
            s3c.create_bucket(Bucket=bucket)
        except Exception as err:
            print("An exception occurred while creating the "
                  + f"{bucket} bucket.  "
                  + f"Details: {err}")
            sys.exit()

    # bucket either already exists or we were able to create it
    # now apply the lifecycle policy
    try:
        print(f"Applying lifecycle policy to {bucket} bucket ...")
        s3c.put_bucket_lifecycle_configuration(Bucket=bucket,
                                               LifecycleConfiguration=lifecycle_policy)
    except s3c.exceptions.NoSuchBucket:
        print("Bucket does not exist.")
    except ParamValidationError as err:
        print("The provided lifecycle policy is invalid.  Please check "
              + "your policy configuration.  Details:")
        print(f"{err}")
    except Exception as err:
        print(err)
