"""
GitHub WebHook receiver for AWS Lambda.

Python based AWS lambda function that receives GitHub WebHooks
and publishes them to SNS topics.
"""

import hashlib
import hmac
import json
import os

import boto3
from chalice import BadRequestError, Chalice, UnauthorizedError

CONFIG = {
    'DEBUG': os.environ.get('DEBUG', '') in [1, '1', 'True', 'true'],
    'SECRET': os.environ.get('SECRET'),
    'S3_REGION': os.environ.get('S3_REGION', 'eu-west-1'),
}

app = Chalice(app_name='github-webhooks')
app.debug = CONFIG['DEBUG']

SNS = boto3.client('sns', region_name=CONFIG['S3_REGION'])


def validate_signature(request):
    """Validate that the signature in the header matches the payload."""
    if CONFIG['SECRET'] is None:
        return
    try:
        signature = request.headers['X-Hub-Signature']
        _, sha1 = signature.split('=')
    except (KeyError, ValueError):
        raise BadRequestError()
    digest = hmac.new(CONFIG['SECRET'].encode(), request.raw_body.encode(), hashlib.sha1) \
        .hexdigest()
    if not hmac.compare_digest(digest.encode(), sha1.encode()):
        raise UnauthorizedError()


@app.route('/{integration}', methods=['POST'])
def index(integration):
    """Consume GitHub webhook and publish hooks to AWS SNS."""
    request = app.current_request
    validate_signature(request)

    try:
        event = request.headers['X-GitHub-Event']
    except KeyError:
        raise BadRequestError()

    sns_topics = SNS.list_topics()['Topics']
    topic_arns = {
        t['TopicArn'].rsplit(':')[-1]: t['TopicArn']
        for t in sns_topics
        }
    topic = f'{integration}_{event}'
    if topic not in topic_arns.keys():
        topic_arns[topic] = SNS.create_topic(Name=topic)['TopicArn']

    SNS.publish(
        TargetArn=topic_arns[topic],
        Subject=event,
        Message=json.dumps({'default': json.dumps(request.json_body)}),
        MessageStructure='json'
    )

    return {'Code': 'Ok', 'Message': 'Webhook received.'}
