import boto3
import json
import logging
import os
import time
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')
dynamodb = boto3.client('dynamodb')
ssm = boto3.client('ssm')
cloudwatch = boto3.client('cloudwatch')

SHUTDOWN_TAG_KEY = 'AutoShutdown'
SHUTDOWN_TAG_VALUE = 'true'
DRY_RUN = os.environ.get('DRY_RUN', 'false').lower() == 'true'
OVERRIDE_TABLE = os.environ.get('OVERRIDE_TABLE', 'finops-shutdown-overrides')
SLACK_WEBHOOK_PARAM = os.environ.get('SLACK_WEBHOOK_PARAM', '/finops/slack/webhook-url')
METRICS_NAMESPACE = 'FinOps/Scheduler'

HOURLY_COST_USD = 0.0104
USD_TO_INR = 84
WEEKDAY_OFF_HOURS = 15

_webhook_url = None


def emit_metrics(action, affected, skipped, savings_inr):
    try:
        timestamp = datetime.now(timezone.utc)
        cloudwatch.put_metric_data(
            Namespace=METRICS_NAMESPACE,
            MetricData=[
                {'MetricName': 'InstancesAffected', 'Dimensions': [{'Name': 'Action', 'Value': action}], 'Value': affected, 'Unit': 'Count', 'Timestamp': timestamp},
                {'MetricName': 'InstancesSkipped', 'Dimensions': [{'Name': 'Action', 'Value': action}], 'Value': skipped, 'Unit': 'Count', 'Timestamp': timestamp},
                {'MetricName': 'SavingsINR', 'Value': savings_inr, 'Unit': 'None', 'Timestamp': timestamp}
            ]
        )
        logger.info("Metrics emitted: affected=%d skipped=%d savings=%.0f" % (affected, skipped, savings_inr))
    except Exception as e:
        logger.warning("Failed to emit metrics: %s" % e)


def get_slack_webhook():
    global _webhook_url
    if _webhook_url is None:
        response = ssm.get_parameter(Name=SLACK_WEBHOOK_PARAM, WithDecryption=True)
        _webhook_url = response['Parameter']['Value']
    return _webhook_url
def send_slack_notification(action, affected, skipped, instances_affected, instances_skipped, savings_inr):
    try:
        emoji = '🛑' if action == 'stop' else '🟢'
        lines = ["%s *FinOps Scheduler* — action: `%s`" % (emoji, action)]
        lines.append("• Affected: *%d* instance(s)" % affected)
        if instances_affected:
            lines.append("   `%s`" % ', '.join(instances_affected))
        if skipped:
            lines.append("• Skipped (overrides): *%d*" % skipped)
            lines.append("   `%s`" % ', '.join(instances_skipped))
        if action == 'stop' and affected > 0:
            lines.append("• Est. savings tonight: *₹%.0f*" % savings_inr)

        payload = json.dumps({'text': '\n'.join(lines)}).encode('utf-8')
        req = urllib.request.Request(get_slack_webhook(), data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
        logger.info("Slack notification sent")
    except Exception as e:
        logger.warning("Slack notification failed: %s" % e)


def find_managed_instances(state):
    response = ec2.describe_instances(Filters=[
        {'Name': 'tag:%s' % SHUTDOWN_TAG_KEY, 'Values': [SHUTDOWN_TAG_VALUE]},
        {'Name': 'instance-state-name', 'Values': [state]}
    ])
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            tags = {t['Key']: t['Value'] for t in instance.get('Tags', [])}
            instances.append({'id': instance['InstanceId'], 'state': instance['State']['Name'], 'name': tags.get('Name', 'unnamed')})
    return instances


def has_active_override(instance_id):
    try:
        response = dynamodb.get_item(TableName=OVERRIDE_TABLE, Key={'instance_id': {'S': instance_id}})
        if 'Item' not in response:
            return False
        expires_at = int(response['Item']['expires_at']['N'])
        if expires_at < int(time.time()):
            return False
        requested_by = response['Item'].get('requested_by', {}).get('S', 'unknown')
        logger.info("  Override active for %s (by %s)" % (instance_id, requested_by))
        return True
    except Exception as e:
        logger.warning("Override check failed for %s: %s" % (instance_id, e))
        return False


def execute_action(action, instance_ids):
    if action == 'stop':
        ec2.stop_instances(InstanceIds=instance_ids)
    elif action == 'start':
        ec2.start_instances(InstanceIds=instance_ids)


def lambda_handler(event, context):
    action = event.get('action', 'stop')
    target_state = 'running' if action == 'stop' else 'stopped'

    logger.info("Action: %s | DRY_RUN=%s" % (action, DRY_RUN))
    candidates = find_managed_instances(state=target_state)

    affected, skipped = [], []
    for inst in candidates:
        if has_active_override(inst['id']):
            logger.info("  SKIP: %s (%s) - override active" % (inst['id'], inst['name']))
            skipped.append(inst['id'])
        else:
            logger.info("  %s: %s (%s)" % (action.upper(), inst['id'], inst['name']))
            affected.append(inst['id'])

    if not DRY_RUN and affected:
        execute_action(action, affected)
        logger.info("Action '%s' completed: %d affected, %d skipped" % (action, len(affected), len(skipped)))

    savings_inr = len(affected) * HOURLY_COST_USD * WEEKDAY_OFF_HOURS * USD_TO_INR if action == 'stop' else 0

    emit_metrics(action, len(affected), len(skipped), savings_inr)
    send_slack_notification(action, len(affected), len(skipped), affected, skipped, savings_inr)

    return {
        'action': action,
        'affected': len(affected),
        'skipped': len(skipped),
        'savings_inr': round(savings_inr, 2),
        'instances_affected': affected,
        'instances_skipped': skipped
    }
