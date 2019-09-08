from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer

from meiduo.apps.oauth import constants


def check_access_token(access_token):
    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,expires_in=constants.SAVE_QQ_USER_TOKEN_EX)
    try:
        data = serializer.loads(access_token)
    except serializer.BadData:
        return None
    else:
        return data.get('openid')


def generate_access_token(openid):
    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY,expires_in=constants.ACCESS_TOKEN_EXPIRES)
    data = {'openid':openid}
    token = serializer.dumps(data)
    return token.decode()

