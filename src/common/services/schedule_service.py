import boto3
from datetime import timezone, datetime
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class SchedulerService:
    def __init__(self, lambda_arn: str, role_arn: str, region="ap-south-1"):
        self.client = boto3.client("scheduler", region_name=region)
        self.lambda_arn = lambda_arn
        self.role_arn = role_arn

    def schedule_checkout(self, booking_id: str, user_id: str, room_id: str, checkout_time: datetime):
        schedule_name = f"checkout-{booking_id}"
        
        try:
            schedule_expression = self._to_at_expression(checkout_time)
        except ValueError as e:
            logger.error(f"Invalid time format: {e}")
            raise e

        payload = {
            "booking_id": booking_id,
            "room_id": room_id,
            "user_id": user_id
        }
        
        schedule_params = {
            "Name": schedule_name,
            "ScheduleExpression": schedule_expression,
            "ScheduleExpressionTimezone": "UTC",
            "FlexibleTimeWindow": {"Mode": "OFF"},
            "Target": {
                "Arn": self.lambda_arn,
                "RoleArn": self.role_arn,
                "Input": json.dumps(payload),
            },
            "ActionAfterCompletion": "DELETE"
        }

        try:
            self.client.create_schedule(
                **schedule_params,
                ClientToken=booking_id  
            )
            logger.info(f"Scheduled checkout for {booking_id} at {schedule_expression}")
            return True

        except self.client.exceptions.ConflictException:
            logger.info(f"Schedule {schedule_name} exists. Updating target time.")
            
            self.client.update_schedule(
                **schedule_params
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to schedule checkout for {booking_id}")
            raise e

    def _to_at_expression(self, dt: datetime) -> str:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)

        if dt.tzinfo is None:
            raise ValueError("checkout_time must be timezone-aware")

        utc_dt = dt.astimezone(timezone.utc)
        return f"at({utc_dt.strftime('%Y-%m-%dT%H:%M:%S')})"