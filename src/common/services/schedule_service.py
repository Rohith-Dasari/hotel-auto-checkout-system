import boto3
from datetime import timezone
import json

class SchedulerService:
    def __init__(self, lambda_arn, role_arn, region="ap-south-1"):
        self.client = boto3.client("scheduler", region_name=region)
        self.lambda_arn = lambda_arn
        self.role_arn = role_arn

    def schedule_checkout(self, booking_id, room_id, checkout_time):
        schedule_name = f"checkout-{booking_id}"

        self.client.create_schedule(
            Name=schedule_name,
            ScheduleExpression=f"at({checkout_time.astimezone(timezone.utc).isoformat()})",
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": self.lambda_arn,
                "RoleArn": self.role_arn,
                "Input": json.dumps({
                    "booking_id": booking_id,
                    "room_id": room_id
                }),
            }
        )
