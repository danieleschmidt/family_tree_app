# Family Tree App
A Family Tree Web-Application written in Django. 

## Screenshots
### User View

### Login Page
| Log In | Create an account | Authorized page |
| -------|--------------|-----------------|
| <img src="./screenshots/login.png" width="200"> | <img src="./screenshots/create_an_account.png" width="200"> | <img src="./screenshots/authorized_page.png" width="200"> |

| Password reset | Set new password | Password change |
| ---------------|------------------|-----------------|
| <img src="./screenshots/password_reset.png" width="200"> | <img src="./screenshots/set_new_password.png" width="200"> | <img src="./screenshots/password_change.png" width="200"> |

## Functionality
### Login Page:
- Log in
    - via username & password
    - via email & password
    - via email or username & password
    - with a remember me checkbox (optional)
- Create an account
- Log out
- Profile activation via email
- Reset password
- Remind a username
- Resend an activation code
- Change password
- Change email
- Change profile
- Multilingual: English, French, Russian, Simplified Chinese and Spanish

If you need dynamic URLs with the language code, check out https://github.com/egorsmkv/simple-django-login-and-register-dynamic-lang

## Installing

### Clone the project

```bash
git clone https://github.com/danieleschmidt/family_tree_app.git
cd family_tree_app
```

### Install dependencies & activate virtualenv

```bash
pip install poetry

poetry install
poetry shell

pip install -r extra_requirements.txt
```

### Configure the settings (connection to the database, connection to an SMTP server, and other options)

1. Edit `source/app/conf/development/settings.py` if you want to develop the project.

2. Edit `source/app/conf/production/settings.py` if you want to run the project in production.

### Apply migrations

```bash
python source/manage.py migrate
```

### Collect static files (only on a production server)

```bash
python source/manage.py collectstatic
```


### Running

#### Generating a local admin account:
```bash
python source/manage.py createsuperuser
```

#### Running a development server

Just run this command:

```bash
python source/manage.py runserver
```

#### Accessing User Page

Member access through: 
```bash
http://127.0.0.1:8000/
```
Admin access through:
```bash
http://127.0.0.1:8000/admin
```

