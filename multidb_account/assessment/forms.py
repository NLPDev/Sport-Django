from django import forms


class AssessmentAdminForm(forms.ModelForm):
    def clean(self):
        super().clean()
        if self.cleaned_data.get('is_private') and self.cleaned_data.get('is_public_everywhere'):
            raise  forms.ValidationError({
                'is_public_everywhere': 'Could not set both "is_private" and "is_public_everywhere".'})
        return self.cleaned_data
