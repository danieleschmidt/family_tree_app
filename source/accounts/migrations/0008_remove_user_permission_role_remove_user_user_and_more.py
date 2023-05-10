# Generated by Django 4.1.7 on 2023-05-10 21:34

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("accounts", "0007_auto_20230505_1219"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="permission_role",
        ),
        migrations.RemoveField(
            model_name="user",
            name="user",
        ),
        migrations.RemoveField(
            model_name="user",
            name="user_group_role",
        ),
        migrations.RemoveField(
            model_name="user",
            name="user_role",
        ),
        migrations.AddField(
            model_name="user",
            name="date_joined",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="user",
            name="email",
            field=models.EmailField(default="", max_length=255, unique=True),
        ),
        migrations.AddField(
            model_name="user",
            name="first_name",
            field=models.CharField(default="", max_length=30),
        ),
        migrations.AddField(
            model_name="user",
            name="groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                related_name="accounts_user_set",
                related_query_name="user",
                to="auth.group",
                verbose_name="groups",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="is_staff",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="is_superuser",
            field=models.BooleanField(
                default=False,
                help_text="Designates that this user has all permissions without explicitly assigning them.",
                verbose_name="superuser status",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_login",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="last login"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_name",
            field=models.CharField(default="", max_length=30),
        ),
        migrations.AddField(
            model_name="user",
            name="password",
            field=models.CharField(default="", max_length=128, verbose_name="password"),
        ),
        migrations.AddField(
            model_name="user",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Specific permissions for this user.",
                related_name="accounts_user_set",
                related_query_name="user",
                to="auth.permission",
                verbose_name="user permissions",
            ),
        ),
        migrations.AlterField(
            model_name="person",
            name="birthdate",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="person",
            name="email",
            field=models.EmailField(blank=True, default="", max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name="person",
            name="first_name",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="person",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("M", "Male"), ("F", "Female"), ("O", "Other")],
                max_length=1,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="person",
            name="last_name",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="person",
            name="phone",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "permission_role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.userpermissionrole",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="accounts.user"
                    ),
                ),
                (
                    "user_group_role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.usergrouprole",
                    ),
                ),
                (
                    "user_role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.userrole",
                    ),
                ),
            ],
        ),
    ]