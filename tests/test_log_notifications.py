import site
from mock import patch
from os.path import dirname, join
site.addsitedir(join(dirname(dirname(__file__)), 'functions'))

from importlib import import_module

log_notifications = import_module('zoom-log-notifications')


def test_log_notifications_handler(mocker, handler, monkeypatch):
    """
    raw_data is a gzip-compressed, base64-encoded representation of this structure
    {
      "messageType": "DATA_MESSAGE",
      "owner": "542186135646",
      "logGroup": "/aws/lambda/foo-zoom-ingester-zoom-foo-function",
      "logStream": "2018/06/19/[33]abcd1234",
      "subscriptionFilters": [
        "jluker-zoom-ingester-ZoomUploaderLogSubscriptionFilter-SJXIJ5HTP9QJ"
      ],
      "logEvents": [
        {
          "id": "12345",
          "timestamp": 1529421105754,
          "message": "{\"hello\": \"world!\"}"
        },
        {
          "id": "67890",
          "timestamp": 1529421105756,
          "message": "{\"foo\": \"bar\", \"baz\": 54}",
          "exception": "\nTraceback (most recent call last):\n  File \"<doctest...>\", line 10, in <module>\n    lumberjack()\n  File \"<doctest...>\", line 4, in lumberjack\n    bright_side_of_death()\nIndexError: tuple index out of range\n"
        }
      ]
    }
    """

    raw_data = b'\x1f\x8b\x08\x00}4)[\x02\xffmS\xc9v\xa30\x10\xfc\xa0\xb9H\x10\'\xc3\xd1`\x03"\x80\xc7,\x02t\xb3\x90\xcdb\xb0I\x0cf\xf9\xfai\x91INsB\xaf_wuuUq\x9e\x9d\x9e\xa5\xfe\x92%\xa2\xa1v3\xb2\x90\xbc\x12\xc3\xd9\x1fi\xa0\xa7\x08\x9b1\xf6\xf5\x00\xc5\x95kl+\xae\x8a\x81\xa5\xa4:T\xdb\xca\x8f\x8e\xb3\x17\x15\x8a\x17y\xd8\xaf\x8f\n\xa9\xc6\x82\xb4\xd3\x93!1s\x95\x8e\xa4\xbe\x17\xa4\xd2J\xa1zOn\x99}\xd6\x06\xa5\xab\xb0\'\x9f\xf1+W\xb4\xdeM\x9a\x81)t\x11\x16\x9d\xdd\xb4{r\x05\xf5\xac\xd5\x9en\xc20o}tJ\xb4\xe1\x07\x13\xfb(oi\xc9Wnd\xf6v\xfb\x17w\xd9*\xee\xb2\xdf\xb8\xf8\xb1x\x18\x97Y\xeb_\xbd\x88,\xbeA\x1e\xc0\x7f\x11\x89\xb3d\xaa\xd3\xe5v\xd0qec\x9d\x92\t\xb1\xd4Y$\xafdv>\xb8M?\xe1\x96\xfe\x0c;y\x88;\xde\x8a&W\x83&\xaf\xf0I\xf2\xa3\xa9\xfe\xe0\x8ay\x85\x19\x8f+"\xfa?\x1e\xe9c\xd4ea|\xc7\xa1\x19\x1c\x0f\xd4|\'\r\x92\xfbaV\x98\xa2\xa5\x83\xb0=\xd0K\xe7\xe7\xd9\xe9\x98\xb1\xf2\x9f\xbc\xdaC~\xb8\xf2\x84;\xb1\xdc[\xf2t+u\x9d\xfc\x88l\xfc\x1d\xf4D[\xec/1ZuO\xe8\x92+\xe6\xed\x9f7o\xa9\xe1\xdcY2=8\x1e%vNn\xe2\x99\xb7\xd3\x95\xd0\xb1\xba\x84\x8e\xe6\x1a\xfa\x1bi\x9b\xeb\xeaA\x9d\xa9\x87\xddu\\\xb5\xbc\x01\xf7Djn\xf6\xb9\xe4\xb2\xdbc\xaf\xbe"\xaf\xdeO\xde.V\xfd(\x93\x9c~\xf2\xb0\xce\xdf\xfa\x9c\xb4\xe0\xdb\xf7\xae\xd6)\xf3f\x84<|\xbd\xcf\x8d\xac\x03W\x1b\xad\x19aiY\xb3T\xff\xf2O\xce7\xd3@m\xa7\xcc\x14Ze\x89\xffI\x8c\xb2\xe7\xaa\x8f\x88\xed4P\x1b\x84\xa1\xd7\x19\xdcB\xac\xa9\xcc\xd5cw\x80~b\xe8R\xdf\x86\x98c\xf5\xc7\n\x9e\x99\xf4E=\x0en\xf5\xf2+\x95\xfeZ\x13\xf8\x15\x17\xa0\x11\xbc\x9b\x81\xec\xa6\x9e+\x01\xe6V\xfc+\xb5^\nbl\x0b\xf0\x172G\xe7Sk\xd6\xa7\xb9\xe8\xd6\xfa\x9eu\xd0S\x00\xc6ofi5do\x11\xc6\xcb\xe0\xd6\x9b\\\xea\xc3\x01\x8b\x85[\xd0\\\xefx\xa5?D\x82\xe1\x1e\xe7C\xf2\xfe\xc6\xcdn\xe0\xa3R\xa2T\xf5;f\xd1\x0bW\xd8\x05\xbe\xa5\xb0\x8a\xfb;\x9d\x860\xd9@fJ3\xbf9\xcf\x1c\xee\x176\x1d\xe5\xce\xd3Z/\n\xf87\x10\xb1\xb4\x16\xee/e\xe6\x00\xb7\xbaP\xac\xfd\x05i\x18j\x84\x88\x03\x00\x00'

    event = { 'awslogs': { 'data': raw_data } }

    mock_sns = mocker.Mock()
    monkeypatch.setattr(log_notifications, 'sns', mock_sns)
    monkeypatch.setattr(log_notifications, 'SNS_TOPIC_ARN', 'MYTOPIC')

    context = mocker.Mock(invoked_function_arn="arn:aws:lambda:us-east-1:123456789:function:foo")

    handler(log_notifications, event, context)

    publish_args = mock_sns.publish.call_args[1]

    assert publish_args['TopicArn'] == 'MYTOPIC'
    assert publish_args['Subject'] == '[ERROR] foo-zoom-ingester-zoom-foo-function'

    log_stream_url = "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logEventViewer:group=/aws/lambda/foo-zoom-ingester-zoom-foo-function;stream=2018/06/19/[33]abcd1234"

    assert log_stream_url in publish_args['Message']
    assert 'IndexError: tuple index out of range' in publish_args['Message']

