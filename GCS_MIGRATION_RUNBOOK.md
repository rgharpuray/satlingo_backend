# S3 → GCS Migration Runbook (Keuvi)

This runbook covers moving all diagram images from AWS S3 to Google Cloud Storage and updating the app to use GCS. **No data is lost**: we copy every object and update DB URLs before retiring S3.

---

## 1. GCS bucket configuration

Your bucket **`keuvi-app`** is in project **The Playoff Games**, region **us (multiple regions)**, **Standard** storage, **Not public**.

### 1.1 Make objects publicly readable (required for diagram URLs)

Diagrams are loaded by web and mobile clients via the stored URL. For that to work without signed URLs:

1. In GCP Console: **Cloud Storage → Buckets → keuvi-app → Permissions**.
2. **Grant access**:
   - **Principal:** `allUsers`
   - **Role:** **Storage Object Viewer**
3. If your org uses **Domain Restricted Sharing**, add a project-level override so `allUsers` is allowed for this project, or use another strategy (Load Balancer + Cloud CDN or signed URLs).

After this, URLs like  
`https://storage.googleapis.com/keuvi-app/lessons/<id>/<asset>.png`  
will work in browsers and apps.

### 1.2 Service account for the app

1. **IAM & Admin → Service Accounts** in the same project.
2. Create a service account (e.g. `keuvi-app-backend`) with role **Storage Object Admin** (or **Storage Admin**) on the bucket (or project).
3. Create a **JSON key** and download it. You will paste this into Heroku as one line (see below).

---

## 2. Heroku env vars (set before migration)

Set these **in addition to** existing AWS vars (keep AWS until migration is verified).

```bash
# GCS bucket name (same as your bucket)
heroku config:set GS_BUCKET_NAME=keuvi-app --app keuvi

# GCS credentials: one-line JSON from the service account key file
# Example (replace with your real JSON, no newlines):
heroku config:set GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account","project_id":"...","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...@....iam.gserviceaccount.com",...}' --app keuvi
```

To build the one-line value from the key file:

```bash
# From your machine, with the JSON key file path:
cat /path/to/keuvi-app-backend.json | jq -c . | pbcopy
# Then: heroku config:set GOOGLE_APPLICATION_CREDENTIALS_JSON="$(pbpaste)" --app keuvi
# Or paste the one-line JSON into: heroku config:set GOOGLE_APPLICATION_CREDENTIALS_JSON='<paste>' --app keuvi
```

Optional:

```bash
heroku config:set GS_PROJECT_ID=your-gcp-project-id --app keuvi
```

**Switch new uploads to GCS only after** you’ve run the migration and verified the app. The app uses `USE_GCS = (GS_BUCKET_NAME and GOOGLE_APPLICATION_CREDENTIALS_JSON)`. So once those two are set, **new** uploads go to GCS. To keep new uploads on S3 until after the migration, **do not set** `GOOGLE_APPLICATION_CREDENTIALS_JSON` (or `GS_BUCKET_NAME`) until you’re ready. **Recommended order:**

1. Set `GS_BUCKET_NAME` and `GOOGLE_APPLICATION_CREDENTIALS_JSON` on Heroku.
2. Deploy the code that includes the migration command and the storage backend.
3. Run the migration (copy S3 → GCS, update DB).
4. Verify the site and apps use GCS URLs.
5. Set `USE_GCS=True` by ensuring both GCS vars are set (already done in step 1); new uploads will already be on GCS. Then remove AWS vars when you’re sure nothing uses S3.

---

## 3. Run migration (production)

### 3.1 Backup

```bash
heroku pg:backups:capture --app keuvi
```

### 3.2 Dry-run (no writes)

```bash
heroku run "python manage.py migrate_s3_to_gcs --dry-run" --app keuvi
```

Check the printed “Unique S3 objects to migrate” and “DB reference cells to update” and any sample keys.

### 3.3 Run migration

```bash
heroku run "python manage.py migrate_s3_to_gcs" --app keuvi
```

The command copies each S3 object to GCS at the **same key** (e.g. `lessons/<id>/diagram-1.png`), then updates every `LessonAsset` and `MathAsset` row that pointed at an S3 URL to the new `https://storage.googleapis.com/keuvi-app/...` URL. Missing S3 keys are skipped and logged; the run continues.

### 3.4 Verify

- Open the web app and any lesson/math content that uses diagrams; confirm images load from `https://storage.googleapis.com/keuvi-app/...`.
- Optionally run the dry-run again; you should see 0 S3 refs left (or only refs you chose to leave as-is).

---

## 4. Retire S3

1. Empty and delete the S3 bucket in AWS (or stop writing and treat it as deprecated).
2. Remove AWS env vars from Heroku when you’re satisfied nothing needs them:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_STORAGE_BUCKET_NAME`
   - `AWS_S3_REGION_NAME` (if set)

---

## 5. Code / behaviour summary

- **Storage abstraction:** `api/storage_backend.py` provides `upload_media()`, `delete_media()`, and `s3_url_to_key()`. New uploads use `upload_media()` and go to GCS when `USE_GCS` is true (i.e. when `GS_BUCKET_NAME` and `GOOGLE_APPLICATION_CREDENTIALS_JSON` are set).
- **Models:** Only `LessonAsset.s3_url` and `MathAsset.s3_url` hold these URLs; no schema change. The field names stay; the values change from S3 URLs to GCS URLs.
- **API/clients:** They use the URL stored in the DB. No change needed besides ensuring the bucket is public (or you serve via LB + CDN / signed URLs).
- **Deletes:** When you delete an asset, the app should call `delete_media(stored_url)` so the correct backend (GCS or S3) is used. The storage backend already branches on the URL host.

---

## 6. Checklist

- [ ] GCS bucket `keuvi-app` created.
- [ ] Bucket is public: `allUsers` → **Storage Object Viewer** (or LB/CDN/signed-URL plan in place).
- [ ] Service account with Storage Object Admin (or equivalent) and JSON key created.
- [ ] Heroku: `GS_BUCKET_NAME=keuvi-app` and `GOOGLE_APPLICATION_CREDENTIALS_JSON=<one-line JSON>` set.
- [ ] Code with `storage_backend` and `migrate_s3_to_gcs` deployed.
- [ ] DB backup taken.
- [ ] `migrate_s3_to_gcs --dry-run` reviewed.
- [ ] `migrate_s3_to_gcs` run successfully.
- [ ] App verified: diagrams load from GCS.
- [ ] S3 bucket emptied/deleted; AWS env vars removed when no longer needed.
