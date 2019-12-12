import json
import os
import uuid

import pytest
from app import (
    CONFIG,
    DEFAULT_HASHLIB_BLACKLIST,
    SNS,
    app,
    index,
    parse_hashlib_blacklist,
)
from botocore.stub import Stubber
from chalice import BadRequestError, UnauthorizedError

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(TEST_DIR, "push.json")) as fp:
    push = json.load(fp)


class Request(object):
    def __init__(self, json_body, headers=None):
        self.headers = headers or {}
        self.json_body = json_body
        self.raw_body = json.dumps(json_body)


class TestApp(object):
    @pytest.fixture(autouse=True)
    def _set_up(self, monkeypatch):
        CONFIG["SECRET"] = None

    def test_blacklist_default(self):
        assert parse_hashlib_blacklist(DEFAULT_HASHLIB_BLACKLIST) == set(
            ["crc32", "crc32c", "md4", "md5", "mdc2"]
        )

    def test_blacklist_custom(self):
        assert parse_hashlib_blacklist("SHA1,POLY1305-HMAC,INVENTED") == set(
            ["invented", "sha1", "poly1305-hmac"]
        )

    def test_no_secret(self):
        app.current_request = Request(
            push,
            {
                "X-GitHub-Event": "push",
                "X-Hub-Signature": "whatever",
                "X-GitHub-Delivery": uuid.uuid4().hex,
            },
        )

        stubber = Stubber(SNS)
        stubber.add_response(
            "list_topics", {"Topics": [{"TopicArn": "arn:foo:bar:123_push"}]}
        )
        stubber.add_response("publish", {"MessageId": "1234"})
        with stubber:
            response = index("123")
        assert response == {"Code": "Ok", "Message": "Webhook received."}

    def test_no_signature(self):
        CONFIG["SECRET"] = "very-secret"
        app.current_request = Request(
            push, {"X-GitHub-Event": "push", "X-GitHub-Delivery": uuid.uuid4().hex}
        )

        with pytest.raises(BadRequestError):
            index("123")

    def test_wrong_signature_format(self):
        CONFIG["SECRET"] = "very-secret"
        app.current_request = Request(
            push,
            {
                "X-GitHub-Event": "push",
                "X-Hub-Signature": "whatever",
                "X-GitHub-Delivery": uuid.uuid4().hex,
            },
        )

        with pytest.raises(BadRequestError):
            index("123")

    def test_blacklist_checksum_default(self):
        CONFIG["SECRET"] = "very-secret"
        app.current_request = Request(
            push,
            {
                "X-GitHub-Event": "push",
                "X-Hub-Signature": "crc32=whatever",
                "X-GitHub-Delivery": uuid.uuid4().hex,
            },
        )

        with pytest.raises(BadRequestError):
            index("123")

    def test_blacklist_checksum_custom(self):
        CONFIG["SECRET"] = "very-secret"
        CONFIG["HASHLIB_BLACKLIST"] = set(["poly1305-hmac"])
        app.current_request = Request(
            push,
            {
                "X-GitHub-Event": "push",
                "X-Hub-Signature": "poly1305-hmac=whatever",
                "X-GitHub-Delivery": uuid.uuid4().hex,
            },
        )

        with pytest.raises(BadRequestError):
            index("123")

    def test_wrong_signature(self):
        CONFIG["SECRET"] = "very-secret"
        app.current_request = Request(
            push,
            {
                "X-GitHub-Event": "push",
                "X-Hub-Signature": "sha1=whatever",
                "X-GitHub-Delivery": uuid.uuid4().hex,
            },
        )

        with pytest.raises(UnauthorizedError):
            index("123")

    def test_missing_event_type(self):
        app.current_request = Request(
            push,
            {"X-Hub-Signature": "sha=whatever", "X-GitHub-Delivery": uuid.uuid4().hex},
        )

        with pytest.raises(BadRequestError):
            index("123")

    def test_create_missing_topic(self):
        app.current_request = Request(
            push,
            {
                "X-GitHub-Event": "comment",
                "X-Hub-Signature": "sha=whatever",
                "X-GitHub-Delivery": uuid.uuid4().hex,
            },
        )

        stubber = Stubber(SNS)
        stubber.add_response(
            "list_topics", {"Topics": [{"TopicArn": "arn:foo:bar:push"}]}
        )
        stubber.add_response("create_topic", {"TopicArn": "arn:foo:baz:123_push"})
        stubber.add_response("publish", {"MessageId": "1234"})

        with stubber:
            response = index("123")
        assert response == {"Code": "Ok", "Message": "Webhook received."}
