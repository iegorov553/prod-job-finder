# Vercel Protection Bypass for Automated Testing

## Overview

The staging environment uses **Vercel Password Protection** to prevent unauthorized access. For automated testing and CI/CD workflows, Vercel provides **Protection Bypass for Automation** - a feature that allows bypassing deployment protection using a secret token.

## How It Works

Vercel Password Protection works at the platform level, before requests reach your application. To bypass it for automated tools:

1. Generate a bypass secret in your Vercel project settings
2. Include the secret in your requests via HTTP header or query parameter
3. Vercel recognizes the secret and grants access without manual authentication

## Creating Bypass Secrets

### Method 1: Via Vercel API (Recommended for automation)

```bash
curl -X PATCH \
  "https://api.vercel.com/v1/projects/prod-job-finder/protection-bypass?teamId=ivans-projects-48e4e549" \
  -H "Authorization: Bearer <vercel-token>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Response contains the generated secret:
```json
{
  "protectionBypass": {
    "Olq8fCt7uUuNLdXFtSWaUVdLHPpNtJzS": {
      "scope": "automation-bypass",
      "isEnvVar": true,
      "createdAt": 1770828443825,
      "createdBy": "..."
    }
  }
}
```

### Method 2: Via Vercel Web UI

1. Go to your project settings in Vercel dashboard
2. Navigate to **Deployment Protection** section
3. Find **Protection Bypass for Automation**
4. Click **Generate Secret**
5. Copy the generated secret

## Using Bypass Secrets

### Option 1: HTTP Header (Recommended)

Add the `x-vercel-protection-bypass` header to your requests:

```bash
curl -H "x-vercel-protection-bypass: <secret>" \
  https://prod-job-finder-git-staging-ivans-projects-48e4e549.vercel.app/
```

**JavaScript/Node.js example:**
```javascript
fetch('https://prod-job-finder-git-staging-ivans-projects-48e4e549.vercel.app/', {
  headers: {
    'x-vercel-protection-bypass': 'Olq8fCt7uUuNLdXFtSWaUVdLHPpNtJzS'
  }
})
```

**Python example:**
```python
import requests

headers = {
    'x-vercel-protection-bypass': 'Olq8fCt7uUuNLdXFtSWaUVdLHPpNtJzS'
}
response = requests.get(
    'https://prod-job-finder-git-staging-ivans-projects-48e4e549.vercel.app/',
    headers=headers
)
```

### Option 2: Query Parameter

Append `vercelProtectionBypass` to the URL:

```
https://prod-job-finder-git-staging-ivans-projects-48e4e549.vercel.app/?vercelProtectionBypass=<secret>
```

Vercel will automatically redirect to a clean URL and set a bypass cookie.

## Multiple Secrets

As of January 2026, Vercel supports multiple bypass secrets per project. This allows you to:

- Use different secrets for different workflows (CI/CD, testing, monitoring)
- Rotate secrets without downtime
- Revoke specific secrets without affecting others

To create additional secrets, repeat the API call or use the web UI.

## Managing Secrets

### List existing secrets

Use the Vercel API or check the web UI to see all active bypass secrets.

### Revoke a secret

Via API:
```bash
curl -X PATCH \
  "https://api.vercel.com/v1/projects/prod-job-finder/protection-bypass?teamId=ivans-projects-48e4e549" \
  -H "Authorization: Bearer <vercel-token>" \
  -H "Content-Type: application/json" \
  -d '{"secret": "<secret-to-revoke>", "regenerate": false}'
```

Via Web UI: Navigate to project settings and click "Revoke" next to the secret.

## Security Best Practices

### Storage
- **Never commit secrets to version control**
- Store secrets in environment variables or secure secret management systems
- Use different secrets for different environments

### Rotation
- Rotate secrets regularly (e.g., every 90 days)
- Create a new secret before revoking the old one to avoid downtime
- Update all systems using the old secret

### Access Control
- Limit secret distribution to only necessary team members and systems
- Use separate secrets for different purposes (testing, CI/CD, monitoring)
- Revoke secrets immediately if compromised or no longer needed

### Monitoring
- Audit bypass access in Vercel logs
- Set up alerts for unusual access patterns
- Review active secrets periodically and remove unused ones

## Troubleshooting

### 401 Unauthorized with bypass header

**Possible causes:**
1. Incorrect secret value
2. Secret was revoked
3. Typo in header name (`x-vercel-protection-bypass`)

**Solution:** Verify the secret is correct and active in Vercel project settings.

### Bypass works but application returns errors

The bypass only handles Vercel Password Protection. Application-level authentication or errors are separate. Check:
1. Application logs in Vercel dashboard
2. API endpoint responses
3. Environment variables are correctly set

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run E2E tests on staging
  env:
    VERCEL_BYPASS_SECRET: ${{ secrets.VERCEL_BYPASS_SECRET }}
  run: |
    curl -H "x-vercel-protection-bypass: $VERCEL_BYPASS_SECRET" \
      https://prod-job-finder-git-staging-ivans-projects-48e4e549.vercel.app/
```

### Environment Variables

For deployment-time access, bypass secrets can be set as environment variables:

```bash
vercel env add VERCEL_BYPASS_SECRET preview
# Paste the secret when prompted
```

Then use in your application code to make internal requests to protected deployments.

## References

- [Vercel Protection Bypass for Automation](https://vercel.com/docs/deployment-protection/methods-to-bypass-deployment-protection/protection-bypass-automation)
- [Vercel API: Update Protection Bypass](https://vercel.com/docs/rest-api/reference/endpoints/projects/update-protection-bypass-for-automation)
- [Multiple Secrets Support](https://vercel.com/changelog/protection-bypass-for-automation-multiple-secrets)
- [Password Protection Documentation](https://vercel.com/docs/deployment-protection/methods-to-protect-deployments/password-protection)

## Current Active Secrets

| Secret (last 8 chars) | Created | Purpose |
|----------------------|---------|---------|
| ...NtJzS | 2026-02-11 | Claude Code Testing |

**Note:** Full secrets are never displayed after creation. Store them securely when generated.
