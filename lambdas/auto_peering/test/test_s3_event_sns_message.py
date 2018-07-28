import unittest
import json

from auto_peering.s3_event_sns_message import S3EventSNSMessage


def s3_event_for(eventName, key):
    return {'Records': [
        {'eventName': eventName, 's3': {'object': {'key': key}}}
    ]}


def sns_message_containing(s3_event):
    return {'Records': [{'Sns': {'Message': json.dumps(s3_event)}}]}


class TestS3EventSNSMessage(unittest.TestCase):
    def test_has_action_create_when_event_represents_create(self):
        event = sns_message_containing(
            s3_event_for('ObjectCreated:Put', 'vpc-existence/vpc-4e1ed427'))

        message = S3EventSNSMessage(event)

        self.assertEqual(message.action(), 'provision')

    def test_has_action_destroy_when_event_represents_destroy(self):
        event = sns_message_containing(
            s3_event_for('ObjectRemoved:Delete', 'vpc-existence/vpc-4e1ed427'))

        message = S3EventSNSMessage(event)

        self.assertEqual(message.action(), 'destroy')

    def test_has_action_unknown_when_event_name_is_not_recognised(self):
        event = sns_message_containing(
            s3_event_for('ReducedRedundancyLostObject',
                         'vpc-created/vpc-4e1ed427'))

        message = S3EventSNSMessage(event)

        self.assertEqual(message.action(), 'unknown')

    def test_has_type_extracted_from_object_key(self):
        event = sns_message_containing(
            s3_event_for('ObjectCreated:Put', 'vpc-existence/vpc-4e1ed427'))

        message = S3EventSNSMessage(event)

        self.assertEqual(message.type(), 'vpc-existence')

    def test_has_target_extracted_from_object_key(self):
        event = sns_message_containing(
            s3_event_for('ObjectCreated:Put', 'vpc-existence/vpc-4e1ed427'))

        message = S3EventSNSMessage(event)

        self.assertEqual(message.target(), 'vpc-4e1ed427')


if __name__ == '__main__':
    unittest.main()