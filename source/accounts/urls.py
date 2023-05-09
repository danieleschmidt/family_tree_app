from django.urls import path, include
from django_plotly_dash.views import add_to_session
from django.contrib import admin

from .views import (
    LogInView, ResendActivationCodeView, RemindUsernameView, SignUpView, ActivateView, LogOutView,
    ChangeEmailView, ChangeEmailActivateView, ChangeProfileView, ChangePasswordView,
    RestorePasswordView, RestorePasswordDoneView, RestorePasswordConfirmView,
    FamilyTreeManagementView, FamilyTreeInvitationView, FamilyTreeView, PersonView, CloudStorageView,
    AddFamilyMemberView, user_dashboard, send_invitation
)


app_name = 'accounts'

urlpatterns = [
    path('log-in/', LogInView.as_view(), name='log_in'),
    path('log-out/', LogOutView.as_view(), name='log_out'),

    path('resend/activation-code/', ResendActivationCodeView.as_view(), name='resend_activation_code'),

    path('sign-up/', SignUpView.as_view(), name='sign_up'),
    path('activate/<code>/', ActivateView.as_view(), name='activate'),

    path('restore/password/', RestorePasswordView.as_view(), name='restore_password'),
    path('restore/password/done/', RestorePasswordDoneView.as_view(), name='restore_password_done'),
    path('restore/<uidb64>/<token>/', RestorePasswordConfirmView.as_view(), name='restore_password_confirm'),

    path('remind/username/', RemindUsernameView.as_view(), name='remind_username'),

    path('change/profile/', ChangeProfileView.as_view(), name='change_profile'),
    path('change/password/', ChangePasswordView.as_view(), name='change_password'),
    path('change/email/', ChangeEmailView.as_view(), name='change_email'),
    path('change/email/<code>/', ChangeEmailActivateView.as_view(), name='change_email_activation'),

    path('family_tree_management/', FamilyTreeManagementView.as_view(), name='family_tree_management'),
    path('family_tree_invitation/', FamilyTreeInvitationView.as_view(), name='family_tree_invitation'),
    path('family_tree_view/', FamilyTreeView.as_view(), name='family_tree_view'),
    path('add_family_member/', AddFamilyMemberView.as_view(), name='add_family_member'),

    path('person/<int:person_id>/', PersonView.as_view(), name='person'),

    path('cloud_storage/', CloudStorageView.as_view(), name='cloud_storage'),
    path('django_plotly_dash/', include('django_plotly_dash.urls')),
    path('state/', add_to_session, name="session_state"),
    path('admin/', admin.site.urls),
    path('dashboard/', user_dashboard, name='user_dashboard'),
    path('send-invitation/', send_invitation, name='send_invitation'),
]
