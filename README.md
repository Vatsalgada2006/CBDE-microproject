# ⚠️ CRITICAL SECURITY NOTICE - MUST READ BEFORE DEPLOYMENT

## 🔑 KEY ROTATION REQUIRED BEFORE PUBLIC DEPLOYMENT

**IMPORTANT**: This repository previously contained exposed Firebase service account keys and Flask secret keys in commit history. Before making this repository public-facing or deploying to production, you MUST:

### 1. Rotate Firebase Service Account Key
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Navigate to Project Settings → Service Accounts
3. Click "Generate New Private Key" to create a new key
4. This will automatically invalidate the previous key
5. Download the new JSON file and update your environment variables

### 2. Rotate Flask Secret Key
1. Generate a new random secret key:
   ```bash
   # Using OpenSSL (recommended)
   openssl rand -base64 32
   
   # Or using Python
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. Update the `FLASK_SECRET_KEY` environment variable with the new value

### 3. Update Environment Variables
After rotating both keys, update your `.env` file (or platform environment variables) with:
- New Firebase service account key (from the downloaded JSON)
- New Flask secret key
- Keep other Firebase configuration values the same (project ID, client email, storage bucket)

### 4. Verify Repository Security
Confirm that:
- `.env.backup` and `test_key.pem` have been removed from git history
- `.gitignore` includes `.env.backup`, `*.pem`, and `*.key`
- No sensitive data is exposed in current files or recent commits

---