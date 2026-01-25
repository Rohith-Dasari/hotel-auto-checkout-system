import os
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is not set")


def _generate_policy(principal_id, effect, resource, context=None):
    auth_response = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource,
                }
            ],
        },
    }

    if context:
        auth_response["context"] = {
            k: str(v) for k, v in context.items()
        }

    return auth_response


def _get_stage_arn(method_arn: str) -> str:
    parts = method_arn.split("/")
    return "/".join(parts[:2]) + "/*/*"


def lambda_handler(event, context):
    try:
        headers = event.get("headers") or {}
        token = headers.get("Authorization") or headers.get("authorization")

        if not token:
            raise Exception("Missing Authorization header")

        if token.startswith("Bearer "):
            token = token.replace("Bearer ", "")

        decoded = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp"]},
        )

        user_id = decoded.get("user_id")
        if not user_id:
            raise Exception("Missing user_id in token")

        resource = _get_stage_arn(event["methodArn"])

        return _generate_policy(
            principal_id=user_id,
            effect="Allow",
            resource=resource,
            context={
                "user_id": user_id,
                "email": decoded.get("email", ""),
                "role": decoded.get("role", "user"),
            },
        )

    except jwt.ExpiredSignatureError:
        print("Authorization failed: Token expired")
    except jwt.InvalidTokenError as e:
        print("Authorization failed: Invalid token", str(e))
    except Exception as e:
        print("Authorization failed:", str(e))

    return _generate_policy(
        principal_id="unauthorized",
        effect="Deny",
        resource=_get_stage_arn(event["methodArn"]),
    )
