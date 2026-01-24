import boto3
from datetime import timezone, datetime
import json


class SchedulerService:
    def __init__(self, lambda_arn: str, role_arn: str, region="ap-south-1"):
        self.client = boto3.client("scheduler", region_name=region)
        self.lambda_arn = lambda_arn
        self.role_arn = role_arn

    def schedule_checkout(self, booking_id: str, user_id: str, room_id: str, checkout_time):
        schedule_name = f"checkout-{booking_id}"

        if isinstance(checkout_time, str):
            checkout_time = datetime.fromisoformat(checkout_time)

        schedule_time_utc = checkout_time.astimezone(timezone.utc).isoformat()

        self.client.create_schedule(
            Name=schedule_name,
            ScheduleExpression=f"at({schedule_time_utc})",
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": self.lambda_arn,
                "RoleArn": self.role_arn,
                "Input": json.dumps({
                    "booking_id": booking_id,
                    "room_id": room_id,
                    "user_id": user_id
                }),
            }
        )
