import os
import requests


def expire_users(event):
    url = os.environ.get('EXPIRE_USER_WEB_HOOK')    
    token = os.environ.get('DISABLE_EXPIRED_CUSTOMERS_TOKEN')    
    requests.post(url, json={"token": token})
