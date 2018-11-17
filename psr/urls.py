"""psr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.views.generic import RedirectView

from multidb_account.admin import get_urlpattern_for_every_adminsite
from multidb_account.views import *

urlpatterns = [
    url(r'^admin/', RedirectView.as_view(pattern_name='admin_default:index', permanent=True)),
    url(r'^api/', include('rest_api.urls', namespace='rest_api')),

    url(r'^{}(?P<token>[\w:-]+)/$'.format(django_settings.PSR_APP_CONFIRM_ACCOUNT_PATH),
        ConfirmAccountConfirmTemplate.as_view()),
]

# Add admin site for every localized db
urlpatterns = get_urlpattern_for_every_adminsite() + urlpatterns

if django_settings.DEBUG:
    urlpatterns += [url(r'^reset-password-email-template/$', ResetPasswordEmailTemplate.as_view())]
    urlpatterns += [url(r'^reset-password-confirm-email-template/$', ResetPasswordConfirmEmailTemplate.as_view())]
    urlpatterns += [url(r'^user-invite-email-template/$', UserInviteEmailTemplate.as_view())]
    urlpatterns += [url(r'^welcome-email-template/$', WelcomeEmailTemplate.as_view())]
    urlpatterns += static(django_settings.STATIC_URL, document_root=django_settings.STATIC_ROOT)
    urlpatterns += static(django_settings.MEDIA_URL, document_root=django_settings.MEDIA_ROOT)
