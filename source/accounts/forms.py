from datetime import timedelta

from django import forms
from django.forms import ValidationError
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django.core.mail import send_mail

from .models import Person, FamilyTree
from django.contrib.auth import password_validation


class UserCacheMixin:
    user_cache = None


class SignIn(UserCacheMixin, forms.Form):
    password = forms.CharField(label=_('Password'), strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if settings.USE_REMEMBER_ME:
            self.fields['remember_me'] = forms.BooleanField(label=_('Remember me'), required=False)

    def clean_password(self):
        password = self.cleaned_data['password']

        if not self.user_cache:
            return password

        if not self.user_cache.check_password(password):
            raise ValidationError(_('You entered an invalid password.'))

        return password


class SignInViaUsernameForm(SignIn):
    username = forms.CharField(label=_('Username'))

    @property
    def field_order(self):
        if settings.USE_REMEMBER_ME:
            return ['username', 'password', 'remember_me']
        return ['username', 'password']

    def clean_username(self):
        username = self.cleaned_data['username']

        user = User.objects.filter(username=username).first()
        if not user:
            raise ValidationError(_('You entered an invalid username.'))

        if not user.is_active:
            raise ValidationError(_('This account is not active.'))

        self.user_cache = user

        return username


class EmailForm(UserCacheMixin, forms.Form):
    email = forms.EmailField(label=_('Email'))

    def clean_email(self):
        email = self.cleaned_data['email']

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ValidationError(_('You entered an invalid email address.'))

        if not user.is_active:
            raise ValidationError(_('This account is not active.'))

        self.user_cache = user

        return email


class SignInViaEmailForm(SignIn, EmailForm):
    @property
    def field_order(self):
        if settings.USE_REMEMBER_ME:
            return ['email', 'password', 'remember_me']
        return ['email', 'password']


class EmailOrUsernameForm(UserCacheMixin, forms.Form):
    email_or_username = forms.CharField(label=_('Email or Username'))

    def clean_email_or_username(self):
        email_or_username = self.cleaned_data['email_or_username']

        user = User.objects.filter(Q(username=email_or_username) | Q(email__iexact=email_or_username)).first()
        if not user:
            raise ValidationError(_('You entered an invalid email address or username.'))

        if not user.is_active:
            raise ValidationError(_('This account is not active.'))

        self.user_cache = user

        return email_or_username


class SignInViaEmailOrUsernameForm(SignIn, EmailOrUsernameForm):
    @property
    def field_order(self):
        if settings.USE_REMEMBER_ME:
            return ['email_or_username', 'password', 'remember_me']
        return ['email_or_username', 'password']


class SignUpForm(UserCreationForm):
    email = forms.EmailField(label=_('Email'), help_text=_('Required. Enter an existing email address.'))

    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
    )

    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput,
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    class Meta:
        model = User
        fields = settings.SIGN_UP_FIELDS + ['password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        user_exists = User.objects.filter(email__iexact=email).exists()
        if user_exists:
            raise ValidationError(_('A user with that email address already exists.'))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class ResendActivationCodeForm(UserCacheMixin, forms.Form):
    email_or_username = forms.CharField(label=_('Email or Username'))

    def clean_email_or_username(self):
        email_or_username = self.cleaned_data['email_or_username']

        user = User.objects.filter(Q(username=email_or_username) | Q(email__iexact=email_or_username)).first()
        if not user:
            raise ValidationError(_('You entered an invalid email address or username.'))

        if user.is_active:
            raise ValidationError(_('This account has already been activated.'))

        activation = user.activation_set.first()
        if not activation:
            raise ValidationError(_('Activation code not found.'))

        now_with_shift = timezone.now() - timedelta(hours=24)
        if activation.created_at > now_with_shift:
            raise ValidationError(_('Activation code has already been sent. You can request a new code in 24 hours.'))

        self.user_cache = user

        return email_or_username


class ResendActivationCodeViaEmailForm(UserCacheMixin, forms.Form):
    email = forms.EmailField(label=_('Email'))

    def clean_email(self):
        email = self.cleaned_data['email']

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ValidationError(_('You entered an invalid email address.'))

        if user.is_active:
            raise ValidationError(_('This account has already been activated.'))

        activation = user.activation_set.first()
        if not activation:
            raise ValidationError(_('Activation code not found.'))

        now_with_shift = timezone.now() - timedelta(hours=24)
        if activation.created_at > now_with_shift:
            raise ValidationError(_('Activation code has already been sent. You can request a new code in 24 hours.'))

        self.user_cache = user

        return email


class RestorePasswordForm(EmailForm):
    pass


class RestorePasswordViaEmailOrUsernameForm(EmailOrUsernameForm):
    pass


class ChangeProfileForm(forms.Form):
    first_name = forms.CharField(label=_('First name'), max_length=30, required=False)
    last_name = forms.CharField(label=_('Last name'), max_length=150, required=False)


class ChangeEmailForm(forms.Form):
    email = forms.EmailField(label=_('Email'))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email']

        if email == self.user.email:
            raise ValidationError(_('Please enter another email.'))

        user = User.objects.filter(Q(email__iexact=email) & ~Q(id=self.user.id)).exists()
        if user:
            raise ValidationError(_('You can not use this mail.'))

        return email


class RemindUsernameForm(EmailForm):
    pass


class InvitationForm(forms.Form):
    recipient_email = forms.EmailField(label='Recipient Email')
    #sender_name = forms.CharField(label='Your Name')
    message = forms.CharField(widget=forms.Textarea, label='Message')

    def send_invite(self, sender_name):
        recipient_email = self.cleaned_data['recipient_email']
        #sender_name = self.cleaned_data['sender_name']
        message = self.cleaned_data['message']

        send_mail(
            subject=f'{sender_name} has invited you to join our family tree',
            message=message,
            from_email='invite@PyFamilyTree.me',
            recipient_list=[recipient_email],
            fail_silently=False,
        )


class AddFamilyMemberForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            'first_name', 'middle_name', 'last_name', 'gender', 'birthdate', 'deathdate',
            'profile_photo', 'father', 'mother', 'spouse', 'email', 'phone', 'address',
            'bio', 'personal_storage'
        ]
        widgets = {
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
            'deathdate': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        # Fetch the family_tree from the keyword arguments, then delete it so it doesn't interfere with the super() call
        self.family_tree = kwargs.pop('family_tree', None)
        super().__init__(*args, **kwargs)

        if self.family_tree:
            self.fields['father'].queryset = Person.objects.filter(family_tree=self.family_tree)
            self.fields['mother'].queryset = Person.objects.filter(family_tree=self.family_tree)
            self.fields['spouse'].queryset = Person.objects.filter(family_tree=self.family_tree)

        self.fields['father'].label_from_instance = lambda obj: f'{obj.first_name} {obj.last_name}'
        self.fields['mother'].label_from_instance = lambda obj: f'{obj.first_name} {obj.last_name}'
        self.fields['spouse'].label_from_instance = lambda obj: f'{obj.first_name} {obj.last_name}'


class CreateFamilyTreeForm(forms.ModelForm):
    class Meta:
        model = FamilyTree
        fields = ['name']
        labels = {
            'name': _('Family Tree Name'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})


class FamilyTreeForm(forms.ModelForm):
    class Meta:
        model = FamilyTree
        fields = ['name', 'description']
        labels = {
            'name': _('Family Tree Name'),
            'description': _('Family Tree Description')
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})


class EditPersonInformationForm(forms.ModelForm):

    class Meta:
        model = Person
        fields = ['first_name', 'middle_name', 'last_name', 'gender', 'birthdate', 'deathdate',
                  'profile_photo', 'father', 'mother', 'spouse', 'email', 'phone', 'address', 'bio', 'personal_storage']

        labels = {
            'first_name': _('First Name'),
            'middle_name': _('Middle Name'),
            'last_name': _('Last Name'),
            'gender': _('Gender'),
            'birthdate': _('Birthdate'),
            'deathdate': _('Deathdate'),
            'profile_photo': _('Profile Photo'),
            'father': _('Father'),
            'mother': _('Mother'),
            'spouse': _('Spouse'),
            'email': _('Email'),
            'phone': _('Phone'),
            'address': _('Address'),
            'bio': _('Bio'),
            'personal_storage': _('Personal Storage'),
        }

        widgets = {
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
            'deathdate': forms.DateInput(attrs={'type': 'date'}),
        }


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        exclude = ('id', 'family_tree', 'user')
        labels = {
            'first_name': _('First name'),
            'middle_name': _('Middle name'),
            'last_name': _('Last name'),
            'birthdate': _('Birth date'),
            'deathdate': _('Death date'),
            'profile_photo': _('Profile photo'),
            'father': _('Father'),
            'mother': _('Mother'),
            'spouse': _('Spouse'),
            'email': _('Email'),
            'phone': _('Phone'),
            'address': _('Address'),
            'bio': _('Bio'),
            'personal_storage': _('Personal storage')
        }