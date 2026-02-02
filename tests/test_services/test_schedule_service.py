import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import json

from common.services.schedule_service import SchedulerService


class TestSchedulerService(unittest.TestCase):

    @patch("common.services.schedule_service.boto3.client")
    def setUp(self, mock_boto_client):
        self.mock_client = MagicMock()

        class ConflictException(Exception):
            pass

        self.mock_client.exceptions = MagicMock()
        self.mock_client.exceptions.ConflictException = ConflictException

        mock_boto_client.return_value = self.mock_client

        self.lambda_arn = "arn:aws:lambda:ap-south-1:123:function:checkout"
        self.role_arn = "arn:aws:iam::123:role/scheduler-role"

        self.service = SchedulerService(
            lambda_arn=self.lambda_arn,
            role_arn=self.role_arn
        )

        self.checkout_time = datetime.now(timezone.utc) + timedelta(days=1)

    def test_to_at_expression_success(self):
        expr = self.service._to_at_expression(self.checkout_time)

        self.assertTrue(expr.startswith("at("))
        self.assertTrue(expr.endswith(")"))

    def test_to_at_expression_string_input(self):
        dt_str = self.checkout_time.isoformat()

        expr = self.service._to_at_expression(dt_str)

        self.assertTrue(expr.startswith("at("))

    def test_to_at_expression_no_timezone(self):
        naive = datetime.now()

        with self.assertRaises(ValueError):
            self.service._to_at_expression(naive)

    def test_schedule_checkout_create(self):
        self.mock_client.create_schedule.return_value = {}

        result = self.service.schedule_checkout(
            booking_id="b1",
            user_id="u1",
            room_id="r1",
            checkout_time=self.checkout_time
        )

        self.assertTrue(result)
        self.mock_client.create_schedule.assert_called_once()

        _, kwargs = self.mock_client.create_schedule.call_args

        self.assertEqual(kwargs["Name"], "checkout-b1")
        self.assertEqual(kwargs["Target"]["Arn"], self.lambda_arn)
        self.assertEqual(kwargs["Target"]["RoleArn"], self.role_arn)

        payload = json.loads(kwargs["Target"]["Input"])
        self.assertEqual(payload["booking_id"], "b1")
        self.assertEqual(payload["room_id"], "r1")
        self.assertEqual(payload["user_id"], "u1")

    def test_schedule_checkout_conflict_updates(self):
        conflict = self.mock_client.exceptions.ConflictException()
        self.mock_client.create_schedule.side_effect = conflict

        result = self.service.schedule_checkout(
            booking_id="b1",
            user_id="u1",
            room_id="r1",
            checkout_time=self.checkout_time
        )

        self.assertTrue(result)
        self.mock_client.update_schedule.assert_called_once()

    def test_schedule_checkout_invalid_time(self):
        with self.assertRaises(ValueError):
            self.service.schedule_checkout(
                booking_id="b1",
                user_id="u1",
                room_id="r1",
                checkout_time="invalid-date"
            )

    def test_schedule_checkout_unexpected_exception(self):
        self.mock_client.create_schedule.side_effect = Exception("AWS failure")

        with self.assertRaises(Exception):
            self.service.schedule_checkout(
                booking_id="b1",
                user_id="u1",
                room_id="r1",
                checkout_time=self.checkout_time
            )


if __name__ == "__main__":
    unittest.main()
