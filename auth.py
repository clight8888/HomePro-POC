import os
from authlib.integrations.flask_client import OAuth

def init_oauth(app):
    oauth = OAuth(app)
    authority = f"https://cognito-idp.{os.getenv('COGNITO_REGION')}.amazonaws.com/{os.getenv('COGNITO_USER_POOL_ID')}"
    server_metadata_url = f"{authority}/.well-known/openid-configuration"
    oauth.register(
        name='cognito',
        client_id=os.getenv('COGNITO_CLIENT_ID'),
        client_secret=os.getenv('COGNITO_CLIENT_SECRET'),
        server_metadata_url=server_metadata_url,
        client_kwargs={'scope': 'openid email profile'}
    )
    return oauth