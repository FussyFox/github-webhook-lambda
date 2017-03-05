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

DEBUG = os.environ.get('DEBUG', '') in [1, '1', 'True', 'true']
SECRET = os.environ.get('SECRET')

app = Chalice(app_name='github-webhooks')
app.debug = DEBUG

SNS = boto3.client('sns')


def validate_signature(request):
    """Validate that the signature in the header matches the payload."""
    if SECRET is None:
        return
    try:
        signature = request.headers['X-Hub-Signature']
        _, sha1 = signature.split('=')
    except KeyError:
        raise BadRequestError()
    digest = hmac.new(SECRET, request.raw_body, hashlib.sha1).hexdigest()
    if not hmac.compare_digest(digest, sha1.encode('utf-8')):
        raise UnauthorizedError()


@app.route('/', methods=['POST'])
def index():
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
    if event not in topic_arns.keys():
        topic_arns[event] = SNS.create_topic(Name=event)['TopicArn']

    SNS.publish(
        TargetArn=topic_arns[event],
        Message=json.dumps({'default': json.dumps(request.json_body)}),
        MessageStructure='json'
    )

    return {'Code': 'Ok', 'Message': 'Webhook received.'}
