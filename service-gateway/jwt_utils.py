# jwt_utils.py
import os
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError, DecodeError
from functools import wraps
from flask import request, jsonify, g
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "changeme")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def verify_jwt_token(token):
    """
    Verify JWT token and return payload (claims).
    Raises ExpiredSignatureError, InvalidTokenError on failure.
    """
    if token.startswith("Bearer "):
        token = token.split(" ", 1)[1]

    # decode will raise exceptions we can catch upstream
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return payload

def require_jwt(optional=False):
    """
    Decorator for Flask routes to require/optionally accept JWT.
    If optional=True and token absent or invalid -> continue with g.user_claims = None
    If optional=False and token absent/invalid -> return 401/403
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", None)
            if not auth:
                if optional:
                    g.user_claims = None
                    return f(*args, **kwargs)
                return jsonify({"error": "Authorization header required"}), 401

            try:
                claims = verify_jwt_token(auth)
                # attach claims to request context for downstream use
                g.user_claims = claims
                return f(*args, **kwargs)
            except ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except (InvalidTokenError, DecodeError) as e:
                if optional:
                    g.user_claims = None
                    return f(*args, **kwargs)
                return jsonify({"error": "Invalid token", "details": str(e)}), 401
            except Exception as e:
                # unexpected error
                return jsonify({"error": "Token validation error", "details": str(e)}), 401

        return wrapper
    return decorator
