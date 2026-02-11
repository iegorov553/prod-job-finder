# Staging Authentication

## Overview

The staging environment is protected with a simple password-based authentication to prevent unauthorized access while still allowing testing and demonstration.

## How It Works

1. **Middleware Protection**: All routes except `/login` and `/api/auth/*` require authentication
2. **Cookie-based Sessions**: Authentication state is stored in a secure HTTP-only cookie (`staging_auth`)
3. **Environment Variable**: Password is configured via `STAGING_PASSWORD` environment variable

## Setup

### 1. Set Environment Variable

Add to your `.env` or configure in your deployment platform (Vercel, Railway, etc.):

```bash
STAGING_PASSWORD=your_secure_password_here
```

### 2. Deploy

The authentication is automatically active when `STAGING_PASSWORD` is set.

## Usage

### Login

1. Navigate to your staging URL (e.g., `https://staging.example.com`)
2. You'll be redirected to `/login`
3. Enter the password configured in `STAGING_PASSWORD`
4. Click "Sign in"
5. You'll be redirected to the dashboard

### Logout

Click the "Logout" button in the top navigation bar to clear your session.

## Implementation Details

### Files

- `src/middleware.ts`: Middleware that checks authentication for all routes
- `src/app/login/page.tsx`: Login page UI
- `src/app/api/auth/login/route.ts`: API endpoint for password verification
- `src/app/api/auth/logout/route.ts`: API endpoint for clearing session
- `src/components/LogoutButton.tsx`: Client-side logout button component

### Security Considerations

- Cookie is HTTP-only (not accessible via JavaScript)
- Cookie is Secure in production (HTTPS only)
- Cookie has SameSite=Lax protection
- Cookie expires after 7 days
- Default password is used if `STAGING_PASSWORD` is not set (for local development)

### Limitations

This is a **simple authentication mechanism** suitable for staging/demo environments only:

- ✅ Protects staging from casual access
- ✅ Simple to set up and use
- ✅ No database required
- ❌ Not suitable for production
- ❌ Single shared password (no user accounts)
- ❌ No password reset functionality

## Testing

You can test the authentication flow locally:

```bash
# Set password
export STAGING_PASSWORD=test123

# Run dev server
cd apps/web
npm run dev

# Visit http://localhost:3000
# You'll be redirected to /login
# Enter "test123" to access the app
```

## Disabling Authentication

To disable authentication (e.g., for local development):

1. Don't set `STAGING_PASSWORD` environment variable, or
2. Remove/comment out the middleware in `src/middleware.ts`

## Troubleshooting

### Can't login after deployment

- Check that `STAGING_PASSWORD` is correctly set in your deployment platform
- Check deployment logs for any middleware errors
- Try clearing browser cookies and retry

### Redirects in a loop

- Ensure `/login` and `/api/auth/*` are excluded from middleware matcher
- Check that cookies are being set correctly (check browser DevTools > Application > Cookies)

### Logout doesn't work

- Check that the cookie is being cleared (browser DevTools)
- Try clearing all cookies manually
- Check that `/api/auth/logout` is accessible
