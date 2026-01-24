import os
import jwt  

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")


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


def lambda_handler(event, context):
    try:
        token = event["authorizationToken"]

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

        return _generate_policy(
            principal_id=user_id,
            effect="Allow",
            resource=event["methodArn"],
            context={
                "user_id": user_id,
                "email": decoded.get("email", ""),
                "role": decoded.get("role", "user"),
            },
        )

    except Exception as e:
        print("Authorization failed:", str(e))
        return _generate_policy(
            principal_id="unauthorized",
            effect="Deny",
            resource=event["methodArn"],
        )
