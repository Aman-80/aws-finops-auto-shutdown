"""Unit tests for the FinOps scheduler Lambda."""
import time
import boto3
import pytest


def test_find_managed_instances_returns_tagged_running(tagged_instance):
    """Lambda should find instances tagged AutoShutdown=true in running state."""
    import handler
    instances = handler.find_managed_instances(state='running')
    assert len(instances) == 1
    assert instances[0]['id'] == tagged_instance
    assert instances[0]['name'] == 'test-instance'


def test_find_managed_instances_skips_untagged(mock_aws_services):
    """Lambda should ignore instances without AutoShutdown tag."""
    ec2 = boto3.client('ec2', region_name='ap-south-1')
    ec2.run_instances(ImageId='ami-0abcdef1234567890', InstanceType='t3.micro',
                      MinCount=1, MaxCount=1)
    import handler
    instances = handler.find_managed_instances(state='running')
    assert len(instances) == 0


def test_has_active_override_returns_false_when_no_entry(override_table):
    """No DynamoDB entry → no override."""
    import handler
    assert handler.has_active_override('i-nonexistent') is False


def test_has_active_override_returns_true_when_active(override_table):
    """Active (non-expired) override → true."""
    dynamodb = boto3.client('dynamodb', region_name='ap-south-1')
    dynamodb.put_item(
        TableName='finops-shutdown-overrides',
        Item={
            'instance_id': {'S': 'i-test123'},
            'requested_by': {'S': 'developer'},
            'expires_at': {'N': str(int(time.time()) + 3600)}  # 1h future
        }
    )
    import handler
    assert handler.has_active_override('i-test123') is True


def test_has_active_override_returns_false_when_expired(override_table):
    """Expired override (past TTL) → false (fail-safe)."""
    dynamodb = boto3.client('dynamodb', region_name='ap-south-1')
    dynamodb.put_item(
        TableName='finops-shutdown-overrides',
        Item={
            'instance_id': {'S': 'i-expired'},
            'requested_by': {'S': 'developer'},
            'expires_at': {'N': str(int(time.time()) - 3600)}  # 1h past
        }
    )
    import handler
    assert handler.has_active_override('i-expired') is False
