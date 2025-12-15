# Deployment Failure Analysis - December 1, 2025

## Executive Summary

All 4 commits pushed to the main branch on December 1, 2025 experienced deployment failures in the "Deploy to Google Cloud Run" workflow. The Coverage Report workflow passed for all commits, but the deployment workflow failed due to missing GCP authentication credentials.

## Affected Commits

| Time (UTC) | Commit SHA | Description | Coverage | Deploy |
|------------|------------|-------------|----------|--------|
| 16:05:16 | `931a8e8f` | feat: Add Infrastructure Packaging Agent | ✅ SUCCESS | ❌ FAILURE |
| 16:18:54 | `b6b6f983` | chore: Clean up archive docs | ✅ SUCCESS | ❌ FAILURE |
| 16:23:16 | `b3575dea` | Merge dependabot PR #13 | ✅ SUCCESS | ❌ FAILURE |
| 16:33:27 | `fa4f6de1` | feat: Transform code generator | ✅ SUCCESS | ❌ FAILURE |

## Root Cause

The `.github/workflows/deploy-cloud-run.yml` workflow file requires GCP authentication credentials that are not configured in the repository.

**Specific Issue:** Line 47 of the workflow references `secrets.GCP_SA_KEY`, but this GitHub secret does not exist or is not accessible.

```yaml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}
```

**Error Message from Workflow:**
```
The `google-github-actions/auth` action requires one of the following authentication methods:
- credentials_json
- workload_identity_provider + service_account
```

## Impact

- **Code Quality:** Not affected - all tests passed
- **Coverage:** Not affected - coverage reports generated successfully  
- **Deployments:** ALL deployments to Google Cloud Run failed
- **Production:** Service not updated with the latest code changes

## Resolution Options

### Option 1: Configure Service Account Key (Quick Fix)

1. **Create a GCP Service Account** (if not exists):
   ```bash
   gcloud iam service-accounts create eventrelay-deploy \
     --display-name="EventRelay Deployment Account"
   ```

2. **Grant Required Permissions**:
   ```bash
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:eventrelay-deploy@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"
   
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:eventrelay-deploy@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"
   
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:eventrelay-deploy@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/artifactregistry.writer"
   ```

3. **Create and Download JSON Key**:
   ```bash
   gcloud iam service-accounts keys create key.json \
     --iam-account=eventrelay-deploy@PROJECT_ID.iam.gserviceaccount.com
   ```

4. **Add Secret to GitHub**:
   - Go to repository Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `GCP_SA_KEY`
   - Value: Paste the entire contents of `key.json`
   - Click "Add secret"

5. **Clean up the key file**:
   ```bash
   rm key.json
   ```

### Option 2: Use Workload Identity Federation (Recommended for Production)

Workload Identity Federation is more secure as it doesn't require storing long-lived credentials.

1. **Update the workflow** (`.github/workflows/deploy-cloud-run.yml` line 45-47):
   ```yaml
   - name: Authenticate to Google Cloud
     uses: google-github-actions/auth@v2
     with:
       workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
       service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
   ```

2. **Configure WIF in GCP** - Follow [GitHub's official guide](https://github.com/google-github-actions/auth#workload-identity-federation-through-a-service-account)

3. **Add GitHub Secrets**:
   - `WIF_PROVIDER`: Format like `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID`
   - `WIF_SERVICE_ACCOUNT`: Email of the service account

## Additional Required Secrets

The workflow also references these secrets that need to be configured:

| Secret Name | Purpose | Where It's Used |
|-------------|---------|-----------------|
| `GCP_PROJECT_ID` | GCP Project ID | Throughout workflow |
| `GCP_SA_KEY` | Service Account credentials | Line 47 |
| `gemini-api-key` | Gemini API access | Line 96 (Secret Manager) |
| `openai-api-key` | OpenAI API access | Line 96 (Secret Manager) |
| `jwt-secret` | JWT signing | Line 96 (Secret Manager) |
| `session-secret` | Session encryption | Line 96 (Secret Manager) |
| `oauth-secret` | OAuth2 flow | Line 96 (Secret Manager) |

**Note:** There are two separate secret systems involved:
- `GCP_SA_KEY` and `GCP_PROJECT_ID` are GitHub Actions secrets used to authenticate the deployment workflow to Google Cloud.
- The API keys and secrets listed in line 96 (`gemini-api-key`, `openai-api-key`, `jwt-secret`, `session-secret`, `oauth-secret`) are stored in GCP Secret Manager and are accessed by the deployed Cloud Run service at runtime. These are **not** GitHub secrets and must be created in GCP Secret Manager.

## Verification Steps

After applying the fix:

1. **Test the workflow**:
   - Make a small, non-breaking change (e.g., update a comment)
   - Push to main branch
   - Monitor the "Deploy to Google Cloud Run" workflow

2. **Check the deployment**:
   ```bash
   # View recent deployments
   gcloud run services describe eventrelay-api --region us-central1
   
   # Check service health
   curl https://YOUR-SERVICE-URL/api/v1/health
   ```

3. **Review logs** if issues persist:
   ```bash
   gcloud run services logs read eventrelay-api --region us-central1 --limit 50
   ```

## Prevention

To prevent similar issues in the future:

1. **Document required secrets** in `docs/README.md` or a dedicated secrets documentation file in the docs directory
2. **Add secret validation** in the workflow (check if secrets exist before attempting deployment)
3. **Set up deployment notifications** to alert on failures
4. **Consider using GCP's Secret Manager** for runtime secrets instead of embedding them in workflow

## Related Files

- `.github/workflows/deploy-cloud-run.yml` - Deployment workflow
- `.github/workflows/coverage.yml` - Coverage workflow (working)
- `Dockerfile.production` - Production Docker configuration

## Timeline

- **16:05 UTC** - First failure (commit 931a8e8f)
- **16:18 UTC** - Second failure (commit b6b6f983)
- **16:23 UTC** - Third failure (commit b3575dea)
- **16:33 UTC** - Fourth failure (commit fa4f6de1)
- **16:49 UTC** - Issue investigated and documented

## Conclusion

The deployment failures were caused by missing GCP authentication credentials. The issue is environmental (missing secrets) rather than code-related. Once the `GCP_SA_KEY` secret is added to the GitHub repository, or the workflow is updated to use Workload Identity Federation, deployments should succeed.

All code changes from December 1st are valid and passed tests. They simply haven't been deployed to production yet.
