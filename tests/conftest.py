import os
import sys
import pytest
import boto3
from moto import mock_aws

# Make handler importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas', 'scheduler'))


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'ap-south-1'


@pytest.fixture
def mock_aws_services(aws_credentials):
    with mock_aws():
        yield


@pytest.fixture
def tagged_instance(mock_aws_services):
    """Create a running EC2 instance with AutoShutdown=true tag."""
    ec2 = boto3.client('ec2', region_name='ap-south-1')
    response = ec2.run_instances(
        ImageId='ami-0abcdef1234567890',
        InstanceType='t3.micro',
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'AutoShutdown', 'Value': 'true'},
                {'Key': 'Environment', 'Value': 'dev'},
                {'Key': 'Name', 'Value': 'test-instance'}
            ]
        }]
    )
    return response['Instances'][0]['InstanceId']


@pytest.fixture
def override_table(mock_aws_services):
    """Create the DynamoDB overrides table."""
    dynamodb = boto3.client('dynamodb', region_name='ap-south-1')
    dynamodb.create_table(
        TableName='finops-shutdown-overrides',
        KeySchema=[{'AttributeName': 'instance_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'instance_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
