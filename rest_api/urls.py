from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

from rest_api.education.views import EducationViewSet
from .help_center.views import HelpCenterReportViewSet, OrganisationSupportViewSet
from .promocode.views import PromocodeViewSet
from .note.views import FileViewSet, AthleteNoteViewSet, CoachNoteViewSet, ReturnToPlayTypeViewSet
from .videos.views import VideoViewSet
from .precompetition.views import PreCompetitionCreateList, PreCompetitionDetail
from .team.views import TeamPreCompetitionList, TeamCreateList, TeamDetail, TeamPictureUpload, TeamRevoke
from .sport.views import SportList, ChosenSport
from .achievements.views import AchievementViewSet, BadgeViewSet
from payment_gateway.views import CardView, SubscriptionView, WebhookView, PaymentView
from .invite.views import UserInvite, UserInviteResend, UserInviteConfirm, UserInviteUnlink, UserInviteRevoke,\
    UserPendingInviteList, TeamPendingInviteList
from .views import AwsHealth, DisableExpiredCustomers
from .goal.views import MyGoalViewSet, UserGoalViewSet
from .user.views import CustomUserLogin, CustomUserLogout, CustomUserRegisterList, CustomUserDetail, \
    CustomUserProfilePictureUpload, CustomUserChangePassword, CustomUserResetPassword, CustomUserResetPasswordConfirm, \
    BaseCustomUserAutocomplete
from .assessment.views import ChosenAssessmentListUpdateCreate, AssessmentTopCategoryPermission, \
    TeamChosenAssessmentListUpdateCreate, AssessmentList, TeamAssessmentsAverage
from .sport_engine.views import SportEngineEventViewSet, SportEngineGameViewSet

root_router = DefaultRouter()
root_router.register(r'goals', MyGoalViewSet, base_name='goal')
root_router.register(r'files', FileViewSet, base_name='file')
root_router.register(r'return_to_play_types', ReturnToPlayTypeViewSet, base_name='return_to_play_type')
root_router.register(r'coachnotes', CoachNoteViewSet, base_name='all-coachnote')
root_router.register(r'athletenotes', AthleteNoteViewSet, base_name='all-athletes')

user_router = DefaultRouter()
user_router.register(r'videos', VideoViewSet, base_name='video')
user_router.register(r'achievements', AchievementViewSet, base_name='achievement')
user_router.register(r'athletenotes', AthleteNoteViewSet, base_name='athletenote')
user_router.register(r'coachnotes', CoachNoteViewSet, base_name='coachnote')

sportengine_router = DefaultRouter()
sportengine_router.register(r'events', SportEngineEventViewSet, base_name='sportengine-event')
sportengine_router.register(r'games', SportEngineGameViewSet, base_name='sportengine-game')


# http://django-autocomplete-light.readthedocs.io/en/3.1.3/tutorial.html#register-the-autocomplete-view
autocomplete_urls = (
    url(r'^user-autocomplete/$', BaseCustomUserAutocomplete.as_view(), name='user-autocomplete'),
)

app_name = 'rest_api'
urlpatterns = [
    url(r'^', include(root_router.urls)),
    url(r'^login/$', CustomUserLogin.as_view(), name="login"),
    url(r'^logout/$', CustomUserLogout.as_view(), name="logout"),
    url(r'^users/$', CustomUserRegisterList.as_view(), name="users"),
    url(r'^badges/$', BadgeViewSet.as_view({'get': 'list'}), name='badge-list'),
    url(r'^help-center-report/$', HelpCenterReportViewSet.as_view({'post': 'create'}), name='help-center-report-list'),
    url(r'^organisation-support/$', OrganisationSupportViewSet.as_view({'post': 'create'}), name='organisation-support-list'),
    url(r'^users/invite/$', UserInvite.as_view(), name="users-invite-send"),
    url(r'^users/promocode/(?P<code>[^/ ]+)/$', PromocodeViewSet.as_view({'get': 'retrieve'}), name="promocode-detail"),
    url(r'^users/invite/resend/$', UserInviteResend.as_view(), name="users-invite-resend"),
    url(r'^users/invite/confirm/$', UserInviteConfirm.as_view(), name="users-invite-confirm"),
    url(r'^users/invite/unlink/$', UserInviteUnlink.as_view(), name="users-invite-unlink"),
    url(r'^users/invite/revoke/$', UserInviteRevoke.as_view(), name="users-invite-revoke"),
    url(r'^users/(?P<uid>[0-9]+)/$', CustomUserDetail.as_view(), name="user-detail"),
    url(r'^users/(?P<uid>[0-9]+)/', include(user_router.urls)),
    url(r'^users/(?P<uid>[0-9]+)/invites/$', UserPendingInviteList.as_view(), name="user-invites"),
    url(r'^users/(?P<uid>[0-9]+)/picture/$', CustomUserProfilePictureUpload.as_view(), name="user-picture"),
    url(r'^users/(?P<uid>[0-9]+)/assessments/$', ChosenAssessmentListUpdateCreate.as_view(), name="chosen-assessments"),
    url(r'^users/(?P<uid>[0-9]+)/goals/$', UserGoalViewSet.as_view({'get': 'list'}), name="user-goals"),
    url(r'^users/(?P<uid>[0-9]+)/assessments/permissions/$', AssessmentTopCategoryPermission.as_view(),
        name="assessment-permissions"),
    url(r'^users/(?P<uid>[0-9]+)/sports/$', ChosenSport.as_view(), name="chosen-sports"),
    url(r'^users/(?P<uid>[0-9]+)/precompetitions/$', PreCompetitionCreateList.as_view(), name='user-precompetitions'),
    url(r'^users/(?P<uid>[0-9]+)/precompetitions/(?P<pcid>[0-9]+)/$', PreCompetitionDetail.as_view(),
        name='user-precompetition-detail'),
    url(r'^users/(?P<uid>[0-9]+)/payment/$', PaymentView.as_view(), name="payment"),
    url(r'^users/(?P<uid>[0-9]+)/payment/card/$', CardView.as_view(), name="payment-card"),
    url(r'^users/(?P<uid>[0-9]+)/payment/plan/$', SubscriptionView.as_view(), name="payment-plan"),
    url(r'^users/(?P<uid>[0-9]+)/educations/(?P<eid>[0-9]+)/$', EducationViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'put': 'update', 'delete': 'destroy'}), name="user-educations"),
    url(r'^users/(?P<uid>[0-9]+)/educations/$', EducationViewSet.as_view({'get': 'list', 'post': 'create'}), name="user-educations"),
    url(r'^teams/$', TeamCreateList.as_view(), name="teams"),
    url(r'^teams/(?P<tid>[0-9]+)/$', TeamDetail.as_view(), name="team-detail"),
    url(r'^teams/(?P<tid>[0-9]+)/invites/$', TeamPendingInviteList.as_view(), name="team-invites"),
    url(r'^teams/(?P<tid>[0-9]+)/picture/$', TeamPictureUpload.as_view(), name="team-picture"),
    url(r'^teams/(?P<tid>[0-9]+)/assessments/$', TeamChosenAssessmentListUpdateCreate.as_view(),
        name="team-assessments"),
    url(r'^teams/(?P<tid>[0-9]+)/assessments/average/$', TeamAssessmentsAverage.as_view(),
        name="team-assessments-average"),
    url(r'^teams/(?P<tid>[0-9]+)/precompetitions/$', TeamPreCompetitionList.as_view(),
        name="team-precompetitions"),
    url(r'^teams/(?P<tid>[0-9]+)/revoke/$', TeamRevoke.as_view(), name="teams-revoke"),
    url(r'^password/change/$', CustomUserChangePassword.as_view(), name="password-change"),
    url(r'^password/reset/$', CustomUserResetPassword.as_view(), name="password-reset"),
    url(r'^password/reset/confirm/$', CustomUserResetPasswordConfirm.as_view(), name="password-reset-confirm"),
    url(r'^sports/$', SportList.as_view(), name="sports"),
    url(r'^assessments/$', AssessmentList.as_view(), name="assessments"),
    url(r'^webhooks/$', WebhookView.as_view(), name="webhooks"),
    url(r'^health/$', AwsHealth.as_view(), name="health"),
    url(r'^disable-expired-customers/$', DisableExpiredCustomers.as_view(), name="disable-expired-customers"),
    url(r'^sport-engine/', include(sportengine_router.urls)),
]
urlpatterns.extend(autocomplete_urls)
