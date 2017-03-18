import json
import os
import uuid

import pytest
from botocore.stub import Stubber
from chalice import BadRequestError
from chalice import UnauthorizedError

from app import app, index, CONFIG, SNS

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(TEST_DIR, 'push.json')) as fp:
    push = json.load(fp)


class Request(object):
    def __init__(self, json_body, headers=None):
        self.headers = headers or {}
        self.json_body = json_body
        self.raw_body = json.dumps(json_body)


class TestApp(object):

    @pytest.fixture(autouse=True)
    def _set_up(self, monkeypatch):
        CONFIG['SECRET'] = None

    def test_no_secret(self):
        app.current_request = Request(push, {
            'X-GitHub-Event': 'push',
            'X-Hub-Signature': 'whatever',
            'X-GitHub-Delivery': uuid.uuid4().hex,
        })

        stubber = Stubber(SNS)
        stubber.add_response('list_topics', {'Topics': [{'TopicArn': 'arn:foo:bar:push'}]})
        stubber.add_response('publish', {'MessageId': '1234'})
        with stubber:
            response = index()
        assert response == {'Code': 'Ok', 'Message': 'Webhook received.'}

    def test_no_signature(self):
        CONFIG['SECRET'] = 'very-secret'
        app.current_request = Request(push, {
            'X-GitHub-Event': 'push',
            'X-GitHub-Delivery': uuid.uuid4().hex,
        })

        with pytest.raises(BadRequestError):
            index()

    def test_wrong_signature_format(self):
        CONFIG['SECRET'] = 'very-secret'
        app.current_request = Request(push, {
            'X-GitHub-Event': 'push',
            'X-Hub-Signature': 'whatever',
            'X-GitHub-Delivery': uuid.uuid4().hex,
        })

        with pytest.raises(BadRequestError):
            index()

    def test_wrong_signature(self):
        CONFIG['SECRET'] = 'very-secret'
        app.current_request = Request(push, {
            'X-GitHub-Event': 'push',
            'X-Hub-Signature': 'sha=whatever',
            'X-GitHub-Delivery': uuid.uuid4().hex,
        })

        with pytest.raises(UnauthorizedError):
            index()

    def test_missing_event_type(self):
        app.current_request = Request(push, {
            'X-Hub-Signature': 'sha=whatever',
            'X-GitHub-Delivery': uuid.uuid4().hex,
        })

        with pytest.raises(BadRequestError):
            index()

    def test_create_missing_topic(self):
        app.current_request = Request(push, {
            'X-GitHub-Event': 'comment',
            'X-Hub-Signature': 'sha=whatever',
            'X-GitHub-Delivery': uuid.uuid4().hex,
        })

        stubber = Stubber(SNS)
        stubber.add_response('list_topics', {'Topics': [{'TopicArn': 'arn:foo:bar:push'}]})
        stubber.add_response('create_topic', {'TopicArn': 'arn:foo:baz:push'})
        stubber.add_response('publish', {'MessageId': '1234'})

        with stubber:
            response = index()
        assert response == {'Code': 'Ok', 'Message': 'Webhook received.'}
