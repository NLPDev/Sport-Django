from dal import autocomplete
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.db.models import Q
from django.http import Http404
from django.template import loader
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from multidb_account.constants import USER_TYPE_ATHLETE, USER_TYPE_ORG
from multidb_account.user.models import BaseCustomUser
from multidb_account.utils import get_user_from_localized_databases
from rest_api.mixins import PasswordSaltMixin

from .serializers import ResetPasswordSerializer, ChangePasswordSerializer, \
    AthleteUserCustomerRegistrationSerializer, AthleteUserCustomerUpdateSerializer, CoachUserListSerializer, \
    AthleteUserCustomerListSerializer, CustomUserLoginSerializer, CoachUserUpdateSerializer, \
    ResetPasswordConfirmSerializer, CoachUserRegistrationSerializer, CustomUserProfilePictureUploadSerializer, \
    OrganisationUserRegistrationSerializer, OrganisationUserListSerializer, OrganisationUserUpdateSerializer

from rest_api.permissions import IsOwnerOrDeny
from .permissions import AllowAnyCreateOrIsAuthenticated

UserModel = get_user_model()


class CustomUserResetPassword(PasswordSaltMixin, APIView):
    """
    An endpoint for forgot user's password.
    """
    permission_classes = (AllowAny,)

    def send_reset_password_email(self):
        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'api_site': django_settings.PSR_API_BASE_URL,
            'reset_password_path': django_settings.PSR_APP_RESET_PASSWORD_PATH,
            'user': self.user,
            'token': signing.dumps(self.user.email, salt=self.salt),
            # 'secure': self.request.is_secure(),
        }

        msg_plain = loader.render_to_string(django_settings.RESET_PASSWORD_EMAIL_TEMPLATE + '.txt', context)
        msg_html = loader.render_to_string(django_settings.RESET_PASSWORD_EMAIL_TEMPLATE + '.html', context)

        subject = _("Reset the password of your Personal Sport Record account")
        send_mail(subject, msg_plain, django_settings.DEFAULT_FROM_EMAIL, [self.user.email], html_message=msg_html)

    def post(self, request, *args, **kwargs):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            self.user = get_user_from_localized_databases(serializer.validated_data.get('email'))
            if self.user:
                try:
                    self.send_reset_password_email()
                except:
                    return Response({u'error': _("Password reset e-mail NOT sent.")},
                                    status=status.HTTP_400_BAD_REQUEST)
                return Response({"detail": _("Password reset e-mail has been sent.")}, status=status.HTTP_200_OK)
            else:
                return Response({u'error': _("User not found")}, status=status.HTTP_404_NOT_FOUND)


class CustomUserResetPasswordConfirm(PasswordSaltMixin, APIView):
    """
    An endpoint for to set new user's password.
    """
    permission_classes = (AllowAny,)

    def send_reset_password_confirm_email(self):
        context = {
            'app_site': django_settings.PSR_APP_BASE_URL,
            'user': self.request.user,
            # 'secure': self.request.is_secure(),
        }

        msg_plain = loader.render_to_string(django_settings.RESET_PASSWORD_CONFIRM_EMAIL_TEMPLATE + '.txt', context)
        msg_html = loader.render_to_string(django_settings.RESET_PASSWORD_CONFIRM_EMAIL_TEMPLATE + '.html', context)

        subject = _("Your Personal Sport Record password has been reset")
        send_mail(subject, msg_plain,
                  django_settings.DEFAULT_FROM_EMAIL,
                  [self.request.user.email],
                  html_message=msg_html)

    def get_object(self, queryset=None):
        return self.request.user

    def post(self, request, *args, **kwargs):
        serializer = ResetPasswordConfirmSerializer(data=request.data, context={'salt': self.salt})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        try:
            self.send_reset_password_confirm_email()
        except:
            pass

        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomUserChangePassword(APIView):
    """
    An endpoint for changing user's password.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'country': request.user.country,
                                                                          'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": _("The new password has been set.")},
            status=status.HTTP_200_OK
        )


class CustomUserLogout(APIView):
    """
    An endpoint for logout.
    """
    permission_classes = (IsAuthenticated,)

    def get_object(self, request):
        try:
            return UserModel.objects.using(request.user.country).get(email=request.user.email)
        except UserModel.DoesNotExist:
            raise Http404

    def get(self, request, format=None):
        """
        Logout authenticated user (set unusable jwt)
        """
        user = self.get_object(request)
        user.set_jwt_last_expired()
        user.save(using=user.country)
        return Response({"details": "Successfully logged out"}, status=status.HTTP_200_OK)


class CustomUserLogin(APIView):
    """
    An endpoint for login.
    """
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = CustomUserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomUserProfilePictureUpload(APIView):
    """
    Upload/Update user's profile picture.
    """
    permission_classes = (IsOwnerOrDeny,)
    parser_classes = (FormParser, MultiPartParser,)

    def get_object(self, request, uid):
        try:
            user = UserModel.objects.using(request.user.country).get(pk=uid)
            # Call to check permissions first
            self.check_object_permissions(self.request, user)
            return user
        except UserModel.DoesNotExist:
            raise Http404

    def put(self, request, uid, format=None):
        """
        Upload/Update user's profile picture
        """
        user = self.get_object(request, uid)
        serializer = CustomUserProfilePictureUploadSerializer(user, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomUserRegisterList(APIView):
    """
    List all users, or create a new user.
    """

    permission_classes = (AllowAnyCreateOrIsAuthenticated,)

    """
    GET: List all users. Disabled until there's a real need for it
    """

    # def get_queryset(self):
    #     return UserModel.objects.using(self.request.user.country).all()
    #
    # def get(self, request, format=None):
    #     """
    #     List all users.
    #     """
    #     queryset = self.get_queryset()
    #     serializer = CustomUserListSerializer(queryset, many=True, context={"request": request})
    #     return Response(serializer.data)

    def post(self, request, format=None):
        """
        Create a new user.
        """
        is_org = request.data and request.data.get('user_type') == USER_TYPE_ORG

        if request.data and request.data.get('user_type') == USER_TYPE_ATHLETE:
            serializer = AthleteUserCustomerRegistrationSerializer(data=request.data, context={"request": request})
        elif is_org:
            serializer = OrganisationUserRegistrationSerializer(data=request.data, context={"request": request})
        else:
            serializer = CoachUserRegistrationSerializer(data=request.data, context={"request": request})

        serializer.is_valid(raise_exception=True)
        serializer.save(is_active=False) if is_org else serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CustomUserDetail(APIView):
    """
    Retrieve, update or delete a user instance.
    """

    permission_classes = (IsOwnerOrDeny,)

    def get_object(self, request, uid):
        try:
            user = UserModel.objects.using(request.user.country).prefetch_related('organisations').get(pk=uid)
            # Call to check permissions first
            self.check_object_permissions(self.request, user)
            return user
        except UserModel.DoesNotExist:
            raise Http404

    def get(self, request, uid, format=None):
        """
        Retrieve user's details.
        """
        user = self.get_object(request, uid)
        map_usertype_to_serializerclass = {
            USER_TYPE_ATHLETE: AthleteUserCustomerListSerializer,
            USER_TYPE_ORG: OrganisationUserListSerializer,
        }
        serializer_class = map_usertype_to_serializerclass.get(user.user_type, CoachUserListSerializer)
        serializer = serializer_class(user, context={"request": request})
        return Response(serializer.data)

    def put(self, request, uid, format=None):
        """
        Update a user.
        """
        user = self.get_object(request, uid)
        map_usertype_to_serializerclass = {
            USER_TYPE_ATHLETE: AthleteUserCustomerUpdateSerializer,
            USER_TYPE_ORG: OrganisationUserUpdateSerializer,
        }
        serializer_class = map_usertype_to_serializerclass.get(user.user_type, CoachUserUpdateSerializer)
        serializer = serializer_class(user, data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, uid, format=None):
        """
        Update a user.
        """
        user = self.get_object(request, uid)
        if user.user_type == USER_TYPE_ATHLETE:
            serializer = AthleteUserCustomerUpdateSerializer(user,
                                                             data=request.data,
                                                             context={"request": request},
                                                             partial=True)
        else:
            serializer = CoachUserUpdateSerializer(user,
                                                   data=request.data,
                                                   context={"request": request},
                                                   partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, uid, format=None):
        """
        Cancel a user.
        """
        user = self.get_object(request, uid)
        if user.user_type == USER_TYPE_ATHLETE:
            user.athleteuser.customer.cancel()
        user.deactivate()
        return Response({"email": user.email}, status=status.HTTP_200_OK)


class BaseCustomUserAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated() or not self.request.user.is_staff:
            return BaseCustomUser.objects.none()

        qs = BaseCustomUser.objects.using(self.request.user.country).all()
        if self.q:
            qs = qs.filter(
                Q(email__istartswith=self.q) |
                Q(first_name__istartswith=self.q) |
                Q(last_name__istartswith=self.q)
            )

        return qs
