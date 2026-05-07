"""
Lambda scheduler — dry-run mode (M3)
Lists EC2 instances tagged for auto-shutdown without taking action.
"""
import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')

SHUTDOWN_TAG_KEY = 'AutoShutdown'
SHUTDOWN_TAG_VALUE = 'true'
DRY_RUN = os.environ.get('DRY_RUN', 'true').lower() == 'true'


def find_managed_instances(state):
    """Find all EC2 instances with AutoShutdown=true tag in given state."""
    response = ec2.describe_instances(Filters=[
        {'Name': f'tag:{SHUTDOWN_TAG_KEY}', 'Values': [SHUTDOWN_TAG_VALUE]},
        {'Name': 'instance-state-name', 'Values': [state]}
    ])

    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            tags = {t['Key']: t['Value'] for t in instance.get('Tags', [])}
            instances.append({
                'id': instance['InstanceId'],
                'state': instance['State']['Name'],
                'type': instance['InstanceType'],
                'name': tags.get('Name', 'unnamed'),
                'environment': tags.get('Environment', 'unknown'),
                'schedule': tags.get('Schedule', 'none')
            })
    return instances


def lambda_handler(event, context):
    """Entry point for Lambda. Currently dry-run only."""
    action = event.get('action', 'stop')
    target_state = 'running' if action == 'stop' else 'stopped'

    logger.info(f"Action: {action} | DRY_RUN={DRY_RUN}")
    logger.info(f"Searching {target_state} instances with {SHUTDOWN_TAG_KEY}={SHUTDOWN_TAG_VALUE}")

    candidates = find_managed_instances(state=target_state)

    if not candidates:
        logger.info(f"No candidates found for '{action}'")
        return {'action': action, 'candidates': 0, 'instances': []}

    logger.info(f"Found {len(candidates)} candidate(s):")
    for inst in candidates:
        logger.info(
            f"  Would {action}: {inst['id']} "
            f"({inst['name']} | {inst['type']} | env={inst['environment']})"
        )

    return {
        'action': action,
        'dry_run': DRY_RUN,
        'candidates': len(candidates),
        'instances': candidates
    }


# Local execution support
if __name__ == '__main__':
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

    test_event = {'action': 'stop'}
    result = lambda_handler(test_event, None)
    print("\n--- Result ---")
    print(result)
