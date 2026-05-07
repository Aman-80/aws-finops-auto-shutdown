"""
Lambda scheduler — with override mechanism (M5)
Stops/starts EC2 instances tagged AutoShutdown=true,
respects developer overrides stored in DynamoDB.
"""
import boto3
import logging
import os
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')
dynamodb = boto3.client('dynamodb')

SHUTDOWN_TAG_KEY = 'AutoShutdown'
SHUTDOWN_TAG_VALUE = 'true'
DRY_RUN = os.environ.get('DRY_RUN', 'false').lower() == 'true'
OVERRIDE_TABLE = os.environ.get('OVERRIDE_TABLE', 'finops-shutdown-overrides')


def find_managed_instances(state):
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
                'name': tags.get('Name', 'unnamed')
            })
    return instances


def has_active_override(instance_id):
    """Check DynamoDB for active developer override. Fail-open on errors."""
    try:
        response = dynamodb.get_item(
            TableName=OVERRIDE_TABLE,
            Key={'instance_id': {'S': instance_id}}
        )
        if 'Item' not in response:
            return False

        # TTL cleanup is async — verify expires_at manually
        expires_at = int(response['Item']['expires_at']['N'])
        if expires_at < int(time.time()):
            return False

        requested_by = response['Item'].get('requested_by', {}).get('S', 'unknown')
        logger.info(f"  Override active for {instance_id} (by {requested_by})")
        return True
    except Exception as e:
        logger.warning(f"Override check failed for {instance_id}: {e}")
        return False  # fail-open: never block scheduler on DynamoDB errors


def execute_action(action, instance_ids):
    if action == 'stop':
        ec2.stop_instances(InstanceIds=instance_ids)
    elif action == 'start':
        ec2.start_instances(InstanceIds=instance_ids)
    else:
        raise ValueError(f"Unknown action: {action}")


def lambda_handler(event, context):
    action = event.get('action', 'stop')
    target_state = 'running' if action == 'stop' else 'stopped'

    logger.info(f"Action: {action} | DRY_RUN={DRY_RUN}")
    candidates = find_managed_instances(state=target_state)

    if not candidates:
        logger.info(f"No candidates found for '{action}'")
        return {'action': action, 'affected': 0, 'skipped': 0}

    affected, skipped = [], []
    for inst in candidates:
        if has_active_override(inst['id']):
            logger.info(f"  SKIP: {inst['id']} ({inst['name']}) — override active")
            skipped.append(inst['id'])
        else:
            logger.info(f"  {action.upper()}: {inst['id']} ({inst['name']})")
            affected.append(inst['id'])

    if DRY_RUN:
        return {'action': action, 'dry_run': True, 'candidates': len(candidates), 'skipped': len(skipped)}

    if affected:
        execute_action(action, affected)
        logger.info(f"Action '{action}' completed: {len(affected)} affected, {len(skipped)} skipped")
    else:
        logger.info(f"All {len(candidates)} candidates skipped due to overrides")

    return {
        'action': action,
        'affected': len(affected),
        'skipped': len(skipped),
        'instances_affected': affected,
        'instances_skipped': skipped
    }


if __name__ == '__main__':
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(h)
    print(lambda_handler({'action': 'stop'}, None))
