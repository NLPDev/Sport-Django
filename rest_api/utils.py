import re
import uuid

from calendar import timegm
from datetime import datetime, timedelta
from urllib.request import urlopen

from rest_framework_jwt.compat import get_username
from rest_framework_jwt.compat import get_username_field
from rest_framework_jwt.settings import api_settings


def custom_jwt_payload_handler(user, timedelta_hours=None):
    username_field = get_username_field()
    username = get_username(user)

    custom_jwt_expiration = timedelta(hours=timedelta_hours) if timedelta_hours else api_settings.JWT_EXPIRATION_DELTA

    payload = {
        'user_id': user.pk,
        'username': username,
        'exp': datetime.utcnow() + custom_jwt_expiration
    }
    if hasattr(user, 'email'):
        payload['email'] = user.email
    if isinstance(user.pk, uuid.UUID):
        payload['user_id'] = str(user.pk)

    payload[username_field] = username

    # Include original issued at time for a brand new token,
    # to allow token refresh
    if api_settings.JWT_ALLOW_REFRESH:
        payload['orig_iat'] = timegm(
            datetime.utcnow().utctimetuple()
        )

    if api_settings.JWT_AUDIENCE is not None:
        payload['aud'] = api_settings.JWT_AUDIENCE

    if api_settings.JWT_ISSUER is not None:
        payload['iss'] = api_settings.JWT_ISSUER

    return payload


def generate_user_jwt_token(user):
    jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

    payload = custom_jwt_payload_handler(user, 24)
    token = jwt_encode_handler(payload)
    return token


def generate_temporary_user_jwt_token(user):
    jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

    payload = custom_jwt_payload_handler(user, 1)
    token = jwt_encode_handler(payload)
    return token


def get_youtube_video_id_from_url(url):
    # https://stackoverflow.com/a/34833500
    regex = r'(?:https?:\/\/)?' \
            r'(?:[0-9A-Z-]+\.)?' \
            r'(?:youtube|youtu|youtube-nocookie)' \
            r'\.' \
            r'(?:com|be)' \
            r'\/(?:watch\?v=|watch\?.+&v=|embed\/|v\/|.+\?v=)?' \
            r'([^&=\n%\?]{11})'

    match = re.search(regex, url, re.IGNORECASE)
    return match.group(1) if match else None


def get_vimeo_video_id_from_url(url):
    # https://github.com/ittus/python-video-ids/blob/master/videos_id/provider/vimeo.py
    regex = r'https?:\/\/' \
            r'(?:www\.|player\.)?' \
            r'vimeo.com\/' \
            r'(?:channels\/(?:\w+\/)?|groups\/' \
            r'(?:[^\/]*)' \
            r'\/videos\/|album\/' \
            r'(?:\d+)' \
            r'\/video\/|video\/|)' \
            r'(\d+)(?:$|\/|\?)'

    match = re.search(regex, url, re.IGNORECASE)
    return match.group(1) if match else None


def grab_video_name_from_url(url):

    # Download html
    html = urlopen(url).read().decode('utf8')

    # Get title from html
    title = re.search(r'"title"\s*:\s*"([^"]+)"', html, re.IGNORECASE).group(1)

    return title


def grab_video_url_from_embed_code(embed_code):
    if embed_code.startswith('http'):
        return embed_code

    # Look for vimeo url
    match = re.search(r'(https?://vimeo.com/\d+)', embed_code, re.IGNORECASE)
    if match:
        return match.group(1)

    # Look for youtube url
    match = re.search(r'src="([^"]+)"', embed_code, re.IGNORECASE)
    if match:
        return match.group(1)

    return embed_code
