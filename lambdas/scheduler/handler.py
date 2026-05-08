"""
Lambda scheduler — full M6
Stops/starts EC2 instances + Slack notifications + override mechanism.
"""
import boto3
import json
import logging
import os
import time
import urllib.request

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')
dynamodb = boto3.client('dynamodb')
ssm = boto3.client('ssm')

SHUTDOWN_TAG_KEY = 'AutoShutdown'
SHUTDOWN_TAG_VALUE = 'true'
DRY_RUN = os.environ.get('DRY_RUN', 'false').lower() == 'true'
OVERRIDE_TABLE = os.environ.get('OVERRIDE_TABLE', 'finops-shutdown-overrides')
SLACK_WEBHOOK_PARAM = os.environ.get('SLACK_WEBHOOK_PARAM', '/finops/slack/webhook-url')

HOURLY_COST_USD = 0.0104
USD_TO_INR = 84
WEEKDAY_OFF_HOURS = 15

_webhook_url = None


def get_slack_webhook():
    global _webhook_url
    if _webhook_url is None:
        response = ssm.get_parameter(Name=SLACK_WEBHOOK_PARAM, WithDecryption=True)
        _webhook_url = response['Parameter']['Value']
    return _webhook_url

def send_slack_notification(action, affected, skipped, instances_affected, instances_skipped):
    try:
        emoji = '🛑' if action == 'stop' else '🟢'
        savings_inr = affected * HOURLY_COST_USD * WEEKDAY_OFF_HOURS * USD_TO_INR

        lines = [f"{emoji} *FinOps Scheduler* — action: `{action}`"]
        lines.append(f"• Affected: *{affected}* instance(s)")
        if instances_affected:
            lines.append(f"   `{', '.join(instances_affected)}`")
        if skipped:
            lines.append(f"• Skipped (overrides): *{skipped}*")
            lines.append(f"   `{', '.join(instances_skipped)}`")
        if action == 'stop' and affected > 0:
            lines.append(f"• Est. savings tonight: *₹{savings_inr:.0f}*")

        payload = json.dumps({'text': '\n'.join(lines)}).encode('utf-8')
        req = urllib.request.Request(
            get_slack_webhook(),
            data=payload,
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
        logger.info("Slack notification sent")
    except Exception as e:
        logger.warning(f"Slack notification failed: {e}")


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
    try:
        response = dynamodb.get_item(
            TableName=OVERRIDE_TABLE,
            Key={'instance_id': {'S': instance_id}}
        )
        if 'Item' not in response:
            return False
        expires_at = int(response['Item']['expires_at']['N'])
        if expires_at < int(time.time()):
            return False
        requested_by = response['Item'].get('requested_by', {}).get('S', 'unknown')
        logger.info(f"  Override active for {instance_id} (by {requested_by})")
        return True
    except Exception as e:
        logger.warning(f"Override check failed for {instance_id}: {e}")
        return False


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
        send_slack_notification(action, 0, 0, [], [])
        return {'action': action, 'affected': 0, 'skipped': 0}

    affected, skipped = [], []
    for inst in candidates:
        if has_active_override(inst['id']):
            logger.info(f"  SKIP: {inst['id']} ({inst['name']}) — override active")
            skipped.append(inst['id'])
        else:
            logger.info(f"  {action.upper()}: {inst['id']} ({inst['name']})")
            affected.append(inst['id'])

    if not DRY_RUN and affected:
        execute_action(action, affected)
        logger.info(f"Action '{action}' completed: {len(affected)} affected, {len(skipped)} skipped")

    send_slack_notification(action, len(affected), len(skipped), affected, skipped)

    return {
        'action': action,
        'affected': len(affected),
        'skipped': len(skipped),
        'instances_affected': affected,
        'instances_skipped': skipped
    }
