# Intelligent Document Management System

A cloud-based document management system with AI-powered document intelligence.

## Features

* User authentication (via Firebase Authentication)
* Cloud storage for documents (Firebase Storage)
* Metadata storage (Firestore)
* Document text extraction
* AI-powered semantic indexing and relationship detection
* Duplicate and version detection
* Action item extraction (deadlines, tasks)
* Document classification
* Intelligent dashboard with relationship views
* Secure sharing and permissions
* Responsive design with dark mode

## Technology Stack

* Backend: Python Flask
* Authentication: Firebase Authentication
* Database: Firestore
* Storage: Firebase Storage
* Frontend: HTML, CSS, JavaScript
* AI/DS: Open-source embeddings, cosine similarity, semantic chunking

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file based on `.env.example` and fill in your Firebase credentials
6. Run the application: `python app.py`

## Documentation

See the `docs` directory for detailed architecture, AI/DS, security, and testing documentation.

## License

MIT
