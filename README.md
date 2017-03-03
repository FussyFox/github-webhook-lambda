# Github Webhook receiver for AWS Lambda

Python based AWS lambda function that can receive GitHub webhooks.

### Installation

Make sure you have the AWS cli tools setup. And clone this repository.

```shell
virtuelenv env -p `which python2`
pip install -U chalice -r requirements.txt
SECRET= chalice deploy
```

Next you need to get to your AWS console and set the Webhooks secret in the
Lambda environment as `SECRET`.

### Usage

This webhook receiver supports all GitHub hooks.
You can decide which one you want to send to your Lambda function.

All hooks will be published to SNS in a separate topic for each hook type.

You can write your own little lambda functions and subscribe to these SNS topics.
