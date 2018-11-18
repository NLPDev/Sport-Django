from dal import autocomplete
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import ugettext_lazy as _

from multidb_account.constants import USER_TYPE_ORG

from .models import BaseCustomUser, Organisation


class OrganisationForm(forms.ModelForm):
    class Meta:
        model = Organisation
        fields = '__all__'
        widgets = {
            'user': autocomplete.ModelSelect2(url='rest_api:user-autocomplete')
        }


class UserFormMixin:
    def _clean_optional_org_field(self, field):
        value = self.data.get(field, '')
        if self.data['user_type'] != USER_TYPE_ORG and not value:
            raise forms.ValidationError('This field is required for non-organisation users.')
        return value

    def clean_last_name(self):
        return self._clean_optional_org_field('last_name')

    def clean_password1(self):
        return self._clean_optional_org_field('password1')

    def clean_password2(self):
        return self._clean_optional_org_field('password2')


class UserCreationForm(UserFormMixin, forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput, required=False)
    last_name = forms.CharField(label='Last name', required=False)

    class Meta:
        model = BaseCustomUser
        fields = ('email', 'is_staff', 'last_name')

    def clean_password2(self):
        super().clean_password2()
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2:
            # Save the provided password in hashed format
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(UserFormMixin, forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField(label=_("Password"),
                                         help_text=_("Raw passwords are not stored, so there is no way to see "
                                                     "this user's password, but you can change the password "
                                                     "using <a href=\"../password/\">this form</a>."))
    last_name = forms.CharField(label='Last name', required=False)

    class Meta:
        model = BaseCustomUser
        exclude = ('id',)

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]
