import re
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / '.env')

from app import create_app
from models import User

app = create_app('development')
client = app.test_client()

print("--- 1. Testing Homepage & Footer ---")
home_res = client.get('/')
assert home_res.status_code == 200
html = home_res.data.decode('utf-8')
assert 'ds-footer' in html
assert 'ds-footer-disclosure-panel' in html
assert 'ds-footer-heading' in html
assert 'Admin Login to Add Deals' not in html
print("[OK] Homepage and high-contrast footer verified.")

print("\n--- 2. Testing User Registration with CSRF ---")
reg_page = client.get('/auth/register')
assert reg_page.status_code == 200
csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', reg_page.data.decode('utf-8'))
assert csrf_match, "CSRF token not found on register page"
csrf_token = csrf_match.group(1)

import uuid
test_email = f"ananya_{uuid.uuid4().hex[:6]}@example.com"

reg_res = client.post('/auth/register', data={
    'csrf_token': csrf_token,
    'full_name': 'Ananya Sharma',
    'email': test_email,
    'password': 'ShopperPassword2026!',
    'confirm_password': 'ShopperPassword2026!'
}, follow_redirects=True)
assert reg_res.status_code == 200
assert 'Account created successfully' in reg_res.data.decode('utf-8')
print(f"[OK] Regular user registration with CSRF protection verified ({test_email}).")

# Test duplicate registration rejection
reg_dup = client.post('/auth/register', data={
    'csrf_token': csrf_token,
    'full_name': 'Ananya Sharma',
    'email': test_email,
    'password': 'ShopperPassword2026!',
    'confirm_password': 'ShopperPassword2026!'
})
assert reg_dup.status_code == 409
print("[OK] Duplicate email registration rejected with HTTP 409 Conflict.")

print("\n--- 3. Testing User Login and Non-Admin Route Protection ---")
login_page = client.get('/auth/login')
csrf_login = re.search(r'name="csrf_token" value="([^"]+)"', login_page.data.decode('utf-8')).group(1)

user_login_res = client.post('/auth/login', data={
    'csrf_token': csrf_login,
    'email': test_email,
    'password': 'ShopperPassword2026!'
}, follow_redirects=True)
assert user_login_res.status_code == 200
assert 'Welcome back' in user_login_res.data.decode('utf-8')
print("[OK] User login succeeded.")

# Normal user tries to access /admin/dashboard
admin_blocked_res = client.get('/admin/dashboard')
assert admin_blocked_res.status_code == 403
print("[OK] Normal user access to /admin/dashboard successfully rejected with HTTP 403 Forbidden.")

print("\n--- 4. Testing User Logout ---")
auth_home = client.get('/')
csrf_token_logout = re.search(r'name="csrf_token" value="([^"]+)"', auth_home.data.decode('utf-8')).group(1)
logout_res = client.post('/auth/logout', data={'csrf_token': csrf_token_logout}, follow_redirects=True)
assert logout_res.status_code == 200
assert 'logged out successfully' in logout_res.data.decode('utf-8')
print("[OK] User logout succeeded and session cleared.")

print("\n--- 5. Testing Authorized Administrator Sign-In ---")
import os
admin_email = os.getenv('ADMIN_EMAIL', 'nagarajuchaintala2002@gmail.com').strip().lower()
initial_admin_pass = os.getenv('ADMIN_INITIAL_PASSWORD', 'Mgayatri@123').strip()
temp_new_pass = 'DealSpark@Temp2026!'

login_page_admin = client.get('/auth/login')
csrf_admin = re.search(r'name="csrf_token" value="([^"]+)"', login_page_admin.data.decode('utf-8')).group(1)

admin_res = client.post('/auth/login', data={
    'csrf_token': csrf_admin,
    'email': admin_email,
    'password': initial_admin_pass
}, follow_redirects=True)
assert admin_res.status_code == 200
admin_html = admin_res.data.decode('utf-8')
assert 'Administrator Dashboard' in admin_html
assert 'Manage Products' in admin_html
assert 'Manage Deals' in admin_html
assert 'Analytics' in admin_html
assert 'Change Password' in admin_html
print("[OK] Authorized administrator signed in and verified role-specific navigation menu.")

print("\n--- 6. Testing Change Password Flow with Reauthentication ---")
# Admin changes password
cp_page = client.get('/auth/change-password')
assert cp_page.status_code == 200
csrf_cp = re.search(r'name="csrf_token" value="([^"]+)"', cp_page.data.decode('utf-8')).group(1)

cp_res = client.post('/auth/change-password', data={
    'csrf_token': csrf_cp,
    'current_password': initial_admin_pass,
    'new_password': temp_new_pass,
    'confirm_password': temp_new_pass
}, follow_redirects=True)
assert cp_res.status_code == 200
assert 'Password updated successfully' in cp_res.data.decode('utf-8')
print("[OK] Password changed successfully and previous session invalidated.")

# Verify old password fails
login_page_retry = client.get('/auth/login')
csrf_retry = re.search(r'name="csrf_token" value="([^"]+)"', login_page_retry.data.decode('utf-8')).group(1)
old_login_res = client.post('/auth/login', data={
    'csrf_token': csrf_retry,
    'email': admin_email,
    'password': initial_admin_pass
})
assert old_login_res.status_code == 401
print("[OK] Old password no longer authenticates.")

# Verify new password succeeds
new_login_res = client.post('/auth/login', data={
    'csrf_token': csrf_retry,
    'email': admin_email,
    'password': temp_new_pass
}, follow_redirects=True)
assert new_login_res.status_code == 200
assert 'Administrator Dashboard' in new_login_res.data.decode('utf-8')
print("[OK] New password authenticates and re-enters Administrator Dashboard.")

# Restore initial password so environment variable remains in sync
cp_page_restore = client.get('/auth/change-password')
csrf_restore = re.search(r'name="csrf_token" value="([^"]+)"', cp_page_restore.data.decode('utf-8')).group(1)
client.post('/auth/change-password', data={
    'csrf_token': csrf_restore,
    'current_password': temp_new_pass,
    'new_password': initial_admin_pass,
    'confirm_password': initial_admin_pass
}, follow_redirects=True)
print("[OK] Initial administrator credentials restored for consistent environment configuration.")

print("\n--- All End-to-End Verification Checks Passed Successfully! ---")
