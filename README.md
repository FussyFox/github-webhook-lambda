# GitHub WebHook receiver for AWS Lambda

Python based AWS lambda function that receives GitHub WebHooks and publishes them to SNS topics.

### Installation

Make sure you have the AWS cli tools setup. Next make sure to clone this repository.

Once you are done, you can get your WebHook receiver online with 3 simple commands.

```shell
virtuelenv env -p `which python2`
pip install -U chalice -r requirements.txt
chalice deploy
```

Next you should to get to your AWS console and set the WebHook's secret in the
Lambda environment with the name `SECRET`.

### Usage

This WebHook receiver supports all GitHub events.
You can but do not need to limit the events you receive.
All events will be published to SNS in a separate topic for each event type.

Now you can write your own little lambda functions,
subscribe to these SNS topics and react to the events.


### Difference to GitHub's build in SNS service

GitHub has [it's own SNS service](https://aws.amazon.com/blogs/compute/dynamic-github-actions-with-aws-lambda/).
The major difference here is you can use the WebHook in
[GibHub Integrations](https://github.com/integrations).
The SNS service on the other hand, needs to be configured
per repository and can not be configured for organisations.

A difference in design is, that each event type is published in a different topic.
