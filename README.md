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

---# IntelliDoc: Intelligent Document Management System

IntelliDoc is a Flask-based web application that integrates Firebase services with AI/DS capabilities to provide intelligent document processing, organization, and retrieval. The system automatically processes uploaded documents to extract text, generate embeddings, classify documents, extract action items, detect duplicates and versions, and identify relationships between documents.

## Project Overview

IntelliDoc addresses common document management pain points through intelligent automation:
- **Automatic ingestion and processing** upon document receipt or upload
- **Content analysis** to extract key information (sender, date, topic, action items)
- **Intelligent organization suggestions** for categorization and tagging
- **Priority detection** for time-sensitive documents
- **Content-aware search** (find by what document contains, not just filename)
- **Natural language queries** (e.g., "find that contract with Acme from last winter")
- **Faceted browsing** by date, type, tags, people mentioned
- **Relationship visualization** showing connected documents
- **AI-powered relevance ranking** for search results
- **Automatic duplicate detection** and version tracking
- **Proactive notifications** for upcoming deadlines (e.g., contract expirations)
- **Secure sharing** with granular permission controls and audit trails

## Implementation Progress

The following checklist tracks completed and pending tasks for production readiness:

### Phase 1: Immediate Fixes (Completed)
- [x] Fix datetime.utcnow() Deprecation
- [x] Implement Proper Logging
- [x] Fix Import and Validation Issues
- [x] Basic Input Validation

### Phase 2: Short-Term Improvements (In Progress)
- [x] Separate Mock Implementations
- [ ] Security Enhancements (rate limiting, security headers, CSP, HSTS, input sanitization)
- [ ] Functionality Improvements (content/metadata search, pagination, improved error responses, file size limits)

### Phase 3: Long-Term Enhancements (Future Work)
- [ ] Comprehensive Testing Strategy (unit, integration, end-to-end tests, CI/CD)
- [ ] Performance Optimization (profiling, ANN libraries, caching, Firestore indexing)
- [ ] Operational Excellence (structured logging with correlation IDs, health check endpoints, audit logging, error tracking)
- [ ] Production Security Hardening (Firebase security rules, brute force protection, upload security, API monitoring)

## Deployment Instructions

IntelliDoc is ready for deployment to Render (free tier) with a Firebase Spark plan (free tier).

### Required Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_SECRET_KEY` | Yes | Secret key for Flask sessions (generate random string) |
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID from Project Settings |
| `FIREBASE_CLIENT_EMAIL` | Yes | Firebase service account email |
| `FIREBASE_PRIVATE_KEY` | Yes | Firebase service account private key (include headers) |
| `FIREBASE_STORAGE_BUCKET` | Yes | Firebase Storage bucket name (format: `your-project-id.appspot.com`) |

### Render Settings
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app -b 0.0.0.0:$PORT --workers 1`
- **Root Directory**: `/` (repo root)
- **Python Version**: Python 3.11 (recommended)

### Deployment Steps
1. Create Firebase project (if not existing) at https://console.firebase.google.com/
2. Enable Authentication, Firestore, and Storage services
3. Generate service account credentials and download JSON file
4. In Render dashboard:
   - Set Build Command: `pip install -r requirements.txt`
   - Set Start Command: `gunicorn app:app -b 0.0.0.0:$PORT --workers 1`
   - Add the 5 required environment variables above
   - Set Python version to 3.11 (optional but recommended)
5. Deploy to Render (push to GitHub and trigger deploy)

### Post-Deployment Verification
- Application should start successfully without errors
- Authentication flow should work (sign in → access protected routes)
- Document upload/download functionality should operate correctly
- All intelligence features (text extraction, embedding, classification) should function
- No storage bucket related errors should appear in logs

## User Journeys

IntelliDoc transforms the document lifecycle through intelligent features:

1. **Document Receipt/Upload**: Automatic processing, content analysis, intelligent organization suggestions, duplicate detection, immediate visibility.
2. **Storage and Retrieval**: Content-aware search, natural language queries, faceted browsing, relationship visualization, timeline views.
3. **Version Management**: Automatic version detection, clear visualization of version history, change highlighting, easy access to previous versions.
4. **Deadline Tracking**: Automatic date extraction from contracts, proactive notifications, contract dashboard, one-click renewal initiation.
5. **Collaboration**: Secure sharing with granular permissions, access tracking, easy revocation, audit trails.
6. **Document Lifecycle**: Outdated document detection, usage tracking, automated archiving suggestions, expiration date detection, retention policy enforcement.
7. **Cross-Document Analysis**: Theme extraction, entity extraction across document sets, timeline views of events, comparison views, question answering across multiple documents.

## Known Limitations and Future Work

- **Current Limitations**: 
  - OCR not yet implemented (planned using pytesseract + pdf2image)
  - LLM integration not yet implemented (planned using free-tier LLM API for RAG and summarization)
  - Mock services used when Firebase credentials are invalid (development mode)
- **Future Enhancements**:
  - Advanced NLP models for better entity recognition
  - Clustering algorithms for automatic document organization
  - Recommendation system for related documents
  - Document versioning with change tracking
  - Collaborative document editing
  - Workflow automation and approval processes
  - Kubernetes deployment for orchestration
  - Comprehensive test automation

## Acknowledgements

This project uses:
- Firebase Authentication, Firestore, and Storage
- Flask web framework
- Sentence-transformers for embeddings
- PyPDF2, python-docx for text extraction
- Bootstrap for frontend styling

---

*Last updated: 2026-08-27*
