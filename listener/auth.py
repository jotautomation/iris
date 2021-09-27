import base64
import os
import bcrypt

# This is our "user database". As you see passwords and users are hardcoded.
USER_ROLES = {
    "Service": '$2b$12$9krtCz3xld.d4JRI2TYixuxhaNiRXysFtiGSPdYzGQ/ilxzJIbHHK',
    "Admin": '$2b$12$6ov3vhUecjQJGHqWsAI/vOHK.PBvrLTY0ZdhZUcvCrZtJyuebM2se',
}


def authenticate(user, password):
    if user in ["Service", "Admin"]:
        if bcrypt.checkpw(password.encode(), USER_ROLES[user].encode()):
            return True

    if user == 'Operator':
        return True
    return False


def get_cookie_secret():
    '''Get a number that should be secure / random enough for our cryptographic needs.'''

    try:
        with open("cookie_secret") as f:
            secret = f.read()
    except FileNotFoundError:
        with open("cookie_secret", 'w') as f:
            secret = base64.b64encode(os.urandom(50)).decode('ascii')
            f.write(secret)
    return secret


if __name__ == "__main__":
    pass
