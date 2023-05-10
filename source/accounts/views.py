from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import login, authenticate, REDIRECT_FIELD_NAME, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LogoutView as BaseLogoutView, PasswordChangeView as BasePasswordChangeView,
    PasswordResetDoneView as BasePasswordResetDoneView, PasswordResetConfirmView as BasePasswordResetConfirmView,
)
from django.shortcuts import get_object_or_404, redirect
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme as is_safe_url
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import View, FormView
from django.conf import settings
from django.contrib.auth.decorators import login_required
import json
from django.urls import reverse, reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.views import generic
from django.shortcuts import redirect
from django.views.generic.edit import FormView
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .forms import ChangeEmailForm, CreateFamilyTreeForm, PersonForm
from .models import Activation
from .utils import send_activation_change_email
from app import settings
from django.utils.functional import SimpleLazyObject

from .utils import (
    send_activation_email, send_reset_password_email, send_forgotten_username_email, send_activation_change_email,
)
from .forms import (
    SignInViaUsernameForm, SignInViaEmailForm, SignInViaEmailOrUsernameForm, SignUpForm,
    RestorePasswordForm, RestorePasswordViaEmailOrUsernameForm, RemindUsernameForm,
    ResendActivationCodeForm, ResendActivationCodeViaEmailForm, ChangeProfileForm, ChangeEmailForm, AddFamilyMemberForm,
    EditPersonInformationForm
)
from .models import Activation, Person, FamilyTree, User, UserPermissionRole, UserGroupRole, UserRole, UserProfile
from .forms import InvitationForm, FamilyTreeForm, PersonForm


class GuestOnlyView(View):
    def dispatch(self, request, *args, **kwargs):
        # Redirect to the index page if the user already authenticated
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)

        return super().dispatch(request, *args, **kwargs)


class LogInView(GuestOnlyView, FormView):
    template_name = 'accounts/log_in.html'

    @staticmethod
    def get_form_class(**kwargs):
        if settings.DISABLE_USERNAME or settings.LOGIN_VIA_EMAIL:
            return SignInViaEmailForm

        if settings.LOGIN_VIA_EMAIL_OR_USERNAME:
            return SignInViaEmailOrUsernameForm

        return SignInViaUsernameForm

    @method_decorator(sensitive_post_parameters('password'))
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        # Sets a test cookie to make sure the user has cookies enabled
        request.session.set_test_cookie()

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        request = self.request

        # If the test cookie worked, go ahead and delete it since its no longer needed
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()

        # The default Django's "remember me" lifetime is 2 weeks and can be changed by modifying
        # the SESSION_COOKIE_AGE settings' option.
        if settings.USE_REMEMBER_ME:
            if not form.cleaned_data['remember_me']:
                request.session.set_expiry(0)

        login(request, form.user_cache)

        redirect_to = request.POST.get(REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME))
        url_is_safe = is_safe_url(redirect_to, allowed_hosts=request.get_host(), require_https=request.is_secure())

        if url_is_safe:
            return redirect(redirect_to)

        return redirect(settings.LOGIN_REDIRECT_URL)


# class SignUpView(generic.CreateView):
#     form_class = SignUpForm
#     success_url = reverse_lazy('accounts:user_dashboard')
#     template_name = 'accounts/sign_up.html'
#
#     def form_valid(self, form):
#         response = super().form_valid(form)
#         user = form.save(commit=False)
#         user.set_password(form.cleaned_data.get('password1'))
#         user.save()
#         user_role = UserRole.objects.get(role_name='Regular')
#         user_group_role = UserGroupRole.objects.get(role_name='Family')
#         user_permission_role = UserPermissionRole.objects.get(role_name='User')
#         user_profile = UserProfile(user=user, user_role=user_role, user_group_role=user_group_role, permission_role=user_permission_role)
#         user_profile.save()
#         return response


# class SignUpView(FormView):
#     template_name = 'accounts/sign-up.html'
#     form_class = SignUpForm
#
#     def form_valid(self, form):
#         user = User.objects.create_user(
#             username=form.cleaned_data['username'],
#             password=form.cleaned_data['password1'],
#             email=form.cleaned_data['email'],
#             first_name=form.cleaned_data['first_name'],
#             last_name=form.cleaned_data['last_name'],
#             user_role=UserRole.objects.get(role_name='Regular'),
#             user_group_role=UserGroupRole.objects.get(group_name='Default'),
#             permission_role=UserPermissionRole.objects.get(permission_name='Read'),
#         )
#         user_profile = UserProfile.objects.create(
#             user=user,
#             date_of_birth=form.cleaned_data['date_of_birth'],
#             profile_picture=form.cleaned_data['profile_picture'],
#         )
#         return redirect('home')


class SignUpView(FormView):
    template_name = 'accounts/sign_up.html'
    form_class = SignUpForm
    success_url = reverse_lazy('accounts:log_in')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password1'])
        user.save()
        return super().form_valid(form)


class ActivateView(View):
    @staticmethod
    def get(request, code):
        act = get_object_or_404(Activation, code=code)

        # Activate profile
        user = act.user
        user.is_active = True
        user.save()

        # Remove the activation record
        act.delete()

        messages.success(request, _('You have successfully activated your account!'))

        return redirect('accounts:log_in')


class ResendActivationCodeView(GuestOnlyView, FormView):
    template_name = 'accounts/resend_activation_code.html'

    @staticmethod
    def get_form_class(**kwargs):
        if settings.DISABLE_USERNAME:
            return ResendActivationCodeViaEmailForm

        return ResendActivationCodeForm

    def form_valid(self, form):
        user = form.user_cache

        activation = user.activation_set.first()
        activation.delete()

        code = get_random_string(20)

        act = Activation()
        act.code = code
        act.user = user
        act.save()

        send_activation_email(self.request, user.email, code)

        messages.success(self.request, _('A new activation code has been sent to your email address.'))

        return redirect('accounts:resend_activation_code')


class RestorePasswordView(GuestOnlyView, FormView):
    template_name = 'accounts/restore_password.html'

    @staticmethod
    def get_form_class(**kwargs):
        if settings.RESTORE_PASSWORD_VIA_EMAIL_OR_USERNAME:
            return RestorePasswordViaEmailOrUsernameForm

        return RestorePasswordForm

    def form_valid(self, form):
        user = form.user_cache
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        if isinstance(uid, bytes):
            uid = uid.decode()

        send_reset_password_email(self.request, user.email, token, uid)

        return redirect('accounts:restore_password_done')


class ChangeProfileView(LoginRequiredMixin, FormView):
    template_name = 'accounts/profile/change_profile.html'
    form_class = ChangeProfileForm

    def get_initial(self):
        user = self.request.user
        initial = super().get_initial()
        initial['first_name'] = user.first_name
        initial['last_name'] = user.last_name
        return initial

    def form_valid(self, form):
        user = self.request.user
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.save()

        messages.success(self.request, _('Profile data has been successfully updated.'))

        return redirect('accounts:change_profile')


class ChangeEmailView(LoginRequiredMixin, FormView):
    template_name = 'accounts/profile/change_email.html'
    form_class = ChangeEmailForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['email'] = self.request.user.email
        return initial

    def form_valid(self, form):
        user = self.request.user
        email = form.cleaned_data['email']

        if settings.ENABLE_ACTIVATION_AFTER_EMAIL_CHANGE:
            code = get_random_string(20)

            act = Activation()
            act.code = code
            act.user = user
            act.email = email
            act.save()

            send_activation_change_email(self.request, email, code)

            messages.success(self.request, _('To complete the change of email address, click on the link sent to it.'))
        else:
            user.email = email
            user.save()

            messages.success(self.request, _('Email successfully changed.'))

        return redirect('accounts:change_email')


def unwrap_simple_lazy_object(obj):
    """
    If the object is a SimpleLazyObject, return its underlying value, otherwise return the object itself
    """
    if isinstance(obj, SimpleLazyObject):
        return obj._wrapped
    else:
        return obj


class ChangeEmailActivateView(View):
    @staticmethod
    def get(request, code):
        act = get_object_or_404(Activation, code=code)

        # Change the email
        user = act.user
        user.email = act.email
        user.save()

        # Remove the activation record
        act.delete()

        messages.success(request, _('You have successfully changed your email!'))

        return redirect('accounts:change_email')


class RemindUsernameView(GuestOnlyView, FormView):
    template_name = 'accounts/remind_username.html'
    form_class = RemindUsernameForm

    def form_valid(self, form):
        user = form.user_cache
        send_forgotten_username_email(user.email, user.username)

        messages.success(self.request, _('Your username has been successfully sent to your email.'))

        return redirect('accounts:remind_username')


class ChangePasswordView(BasePasswordChangeView):
    template_name = 'accounts/profile/change_password.html'

    def form_valid(self, form):
        # Change the password
        user = form.save()

        # Re-authentication
        login(self.request, user)

        messages.success(self.request, _('Your password was changed.'))

        return redirect('accounts:change_password')


class RestorePasswordConfirmView(BasePasswordResetConfirmView):
    template_name = 'accounts/restore_password_confirm.html'

    def form_valid(self, form):
        # Change the password
        form.save()

        messages.success(self.request, _('Your password has been set. You may go ahead and log in now.'))

        return redirect('accounts:log_in')


class RestorePasswordDoneView(BasePasswordResetDoneView):
    template_name = 'accounts/restore_password_done.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)


class LogOutView(LoginRequiredMixin, View):
    template_name = 'accounts/log_out.html'

    def get(self, request):
        logout(request)
        return render(request, self.template_name)


from django.db.models import Q


class AddFamilyMemberView(LoginRequiredMixin, View):
    def get(self, request):
        form = AddFamilyMemberForm()
        return render(request, 'accounts/add_family_member.html', {'form': form})

    def post(self, request):
        form = AddFamilyMemberForm(request.POST, request.FILES)
        if form.is_valid():
            new_person = form.save(commit=False)
            # Get the user's family tree
            family_tree = FamilyTree.objects.get(super_admin=request.user)
            # Assign the user's family tree to the new person
            new_person.family_tree = family_tree
            new_person.save()

            # Check if the new person already exists in the family tree
            existing_person = Person.objects.filter(
                family_tree=family_tree,
                first_name=new_person.first_name,
                middle_name=new_person.middle_name,
                last_name=new_person.last_name,
                gender=new_person.gender,
                birthdate=new_person.birthdate,
                deathdate=new_person.deathdate,
                father=new_person.father,
                mother=new_person.mother,
                spouse=new_person.spouse,
                email=new_person.email,
                phone=new_person.phone,
                address=new_person.address,
                bio=new_person.bio,
                personal_storage=new_person.personal_storage,
            ).first()

            if existing_person:
                messages.warning(request, 'This person already exists in your family tree.')
                return redirect('accounts:family_tree_view')

            messages.success(request, 'New family member added successfully')
            return redirect('accounts:family_tree_view')
        else:
            messages.error(request, 'There was an error with your form. Please try again.')
            return render(request, 'add_family_member.html', {'form': form})


class FamilyTreeManagementView(LoginRequiredMixin, View):
    template_name = 'accounts/family_tree_management.html'

    def get(self, request):
        return render(request, self.template_name)


class FamilyTreeInvitationView(LoginRequiredMixin, View):
    form_class = InvitationForm
    template_name = 'accounts/family_tree_invitation.html'
    success_template_name = 'accounts/invite_sent.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.send_invite(request.user.username)
            return render(request, self.success_template_name)
        return render(request, self.template_name, {'form': form})


def get_family_tree_data(family_tree):
    family_members = Person.objects.filter(family_tree=family_tree)

    family_tree_data = []

    for member in family_members:
        family_tree_data.append({
            "id": member.id,
            "name": member.full_name,
            "gender": member.gender,
            "birth_date": member.birthdate.isoformat(),
            "death_date": member.deathdate.isoformat() if member.deathdate else None,
            "father": member.father.id if member.father else None,
            "mother": member.mother.id if member.mother else None,
            "spouse": member.spouse.id if member.spouse else None
        })

    return json.dumps(family_tree_data)


class FamilyTreeView(LoginRequiredMixin, View):
    template_name = 'accounts/family_tree.html'

    def get(self, request):
        # Fetch the family tree of the logged in user
        try:
            family_tree = FamilyTree.objects.get(super_admin=request.user)
        except FamilyTree.DoesNotExist:
            # Redirect the user to create a family tree
            return redirect('accounts:create_family_tree')

        # Fetch all family members related to the user's family tree
        family_members = Person.objects.filter(family_tree=family_tree)

        # Convert family members and relationships to nodes and edges format
        nodes, edges = self.family_members_to_visjs_data(family_members)

        # Pass the nodes and edges data to the template
        context = {'nodes': nodes, 'edges': edges, 'family_tree': family_tree}
        return render(request, self.template_name, context)

    @staticmethod
    def family_members_to_visjs_data(family_members):
        nodes = []
        edges = []

        for member in family_members:
            # Add a node for each family member
            nodes.append({'id': member.id, 'label': str(member)})

            # Add edges for parents
            if member.father:
                edges.append({'from': member.father.id, 'to': member.id})
            if member.mother:
                edges.append({'from': member.mother.id, 'to': member.id})

        return nodes, edges

    def create_person(self, request, family_tree):
        # Get the submitted form data
        form_data = request.POST
        form_files = request.FILES

        # Create a new Person instance from the form data
        person = Person()
        person.family_tree = family_tree
        person.first_name = form_data['first_name']
        person.last_name = form_data['last_name']
        person.gender = form_data['gender']
        person.date_of_birth = form_data['date_of_birth']
        person.place_of_birth = form_data['place_of_birth']
        person.profile_picture = form_files.get('profile_picture')
        person.save()

        # Add the new person to the user's family tree
        family_tree.add_person(person)

        # Return the newly created person instance
        return person


def get_root_family_members(user):
    return Person.objects.filter(user=user, father=None, mother=None)


class PersonView(View):
    template_name = 'accounts/person.html'  # adjust this to your needs

    def get(self, request, person_id):
        person = get_object_or_404(Person, id=person_id)
        return render(request, self.template_name, {'person': person})


class CloudStorageView(LoginRequiredMixin, View):
    template_name = 'accounts/cloud_storage.html'

    def get(self, request):
        return render(request, self.template_name)


@login_required
def send_invitation(request):
    if request.method == 'POST':
        family_tree_id = request.POST['family_tree_id']
        recipient_email = request.POST['email']
        # Add logic to send an email invitation here
        messages.success(request, 'Invitation sent to {}'.format(recipient_email))
        return redirect('accounts/user_dashboard')


# @login_required
# def user_dashboard(request):
#
#     user = request.user
#     person = Person.objects.filter(user=user).first()
#     context = {'person': person}
#
#     # try to get family tree, if the user is in one
#     try:
#         family_tree = FamilyTree.objects.filter(super_admin=user).first()
#         context.update({'family_tree': family_tree})
#
#     except AttributeError:
#         pass
#
#     if request.method == 'POST':
#         # handle create family tree form submission
#         form = CreateFamilyTreeForm(request.POST)
#
#         if form.is_valid():
#             family_tree = form.save(commit=False)
#             family_tree.super_admin = user
#             family_tree.save()
#             messages.success(request, 'Family tree created successfully.')
#             context.update({'family_tree': family_tree})
#             return redirect('accounts:user_dashboard')
#
#         else:
#             messages.error(request, 'Error creating family tree. Please try again.')
#     else:
#         # display create family tree form
#         form = CreateFamilyTreeForm()
#
#     context.update({'create_family_tree_form': form})
#
#     return render(request, 'accounts/user_dashboard.html', context)

@login_required
def user_dashboard(request):
    user = request.user
    person = Person.objects.filter(user=user).first()
    context = {'person': person}

    # try to get family tree, if the user is in one
    try:
        family_tree = FamilyTree.objects.filter(super_admin=user).first()
        context.update({'family_tree': family_tree})
    except AttributeError:
        pass

    if request.method == 'POST':
        # handle create family tree form submission
        form = CreateFamilyTreeForm(request.POST)
        if form.is_valid():
            family_tree = form.save(commit=False)
            family_tree.super_admin = user
            family_tree.save()
            messages.success(request, 'Family tree created successfully.')
            context.update({'family_tree': family_tree})
            return redirect('accounts:user_dashboard')
        else:
            messages.error(request, 'Error creating family tree. Please try again.')
    else:
        # display create family tree form
        form = CreateFamilyTreeForm()

    context.update({'create_family_tree_form': form})

    if request.method == 'POST' and 'edit_person' in request.POST:
        # handle edit person form submission
        form = EditPersonInformationForm(request.POST, request.FILES, instance=person)
        if form.is_valid():
            form.save()
            messages.success(request, 'Person information updated successfully.')
            return redirect('accounts:user_dashboard')
        else:
            messages.error(request, 'Error updating person information. Please try again.')
    else:
        # display edit person form
        form = EditPersonInformationForm(instance=person)

    context.update({'edit_person_form': form})

    return render(request, 'accounts/user_dashboard.html', context)


class CreateFamilyTreeView(LoginRequiredMixin, View):
    template_name = 'accounts/family_tree_create.html'

    def get(self, request):
        form = CreateFamilyTreeForm()
        context = {'form': form}
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateFamilyTreeForm(request.POST)
        if form.is_valid():
            family_tree_name = form.cleaned_data['name']
            user = request.user

            # Check if a family tree already exists for the user
            if FamilyTree.objects.filter(super_admin=user).exists():
                messages.error(request, _('You already have a family tree.'))
                return redirect('accounts:user_dashboard')

            # Create a new family tree for the user
            family_tree = FamilyTree.objects.create(
                name=family_tree_name,
                super_admin=user
            )

            # Redirect to the family tree page
            messages.success(request, _('Family tree created successfully.'))
            return redirect('accounts:family_tree_view')

        context = {'form': form}
        return render(request, self.template_name, context)


class FamilyTreeManagementView(LoginRequiredMixin, View):
    template_name = 'accounts/family_tree_management.html'
    form_class = FamilyTreeForm

    def get(self, request):
        # Fetch the family tree of the logged in user
        family_tree = get_object_or_404(FamilyTree, super_admin=request.user)

        # Create a form instance with initial data from the family tree
        form = self.form_class(initial={
            'name': family_tree.name,
            'description': family_tree.description,
        })

        context = {'form': form, 'family_tree': family_tree}
        return render(request, self.template_name, context)

    def post(self, request):
        # Fetch the family tree of the logged in user
        family_tree = get_object_or_404(FamilyTree, super_admin=request.user)

        # Create a form instance with the POST data and the family tree instance
        form = self.form_class(request.POST, instance=family_tree)

        if form.is_valid():
            form.save()
            messages.success(request, 'Family tree details updated successfully.')
            return redirect('accounts:family_tree_management')

        context = {'form': form, 'family_tree': family_tree}
        return render(request, self.template_name, context)


@login_required
def edit_person_information(request, person_id):
    person = get_object_or_404(Person, id=person_id)

    if request.method == 'POST':
        form = PersonForm(request.POST, instance=person)
        if form.is_valid():
            form.save()
            return redirect('person_detail', person_id=person.id)
    else:
        form = PersonForm(instance=person)

    return render(request, 'accounts/edit_person_information.html', {'form': form})


@require_http_methods(["GET", "POST"])
def person_detail(request, person_id):
    print('TRYING')
    print(f"Person ID: {person_id}") # added print statement
    person = get_object_or_404(Person, id=person_id)

    if request.method == "POST":
        form = PersonForm(request.POST, request.FILES, instance=person)
        if form.is_valid():
            form.save()
            return redirect('accounts/person_detail', person_id=person.id)
    else:
        form = PersonForm(instance=person)

    context = {'person': person, 'form': form}
    return render(request, 'accounts/person_detail.html', context)