import logging
import uuid
from typing import List, Tuple, Optional, Dict
from services.extraction_service import ExtractionService
from services.embedding_service import EmbeddingService
from services.chunking_service import ChunkingService
from services.action_service import ActionService
from services.classification_service import ClassificationService
from services.duplicate_service import DuplicateService
from services.version_service import VersionService
from services.relationship_service import RelationshipService
from models.document import Document
from models.action import Action
from models.relationship import Relationship
from services.firebase_service import firestore_db
import numpy as np

logger = logging.getLogger(__name__)

class IntelligenceService:
    def __init__(self):
        self.extraction_service = ExtractionService()
        self.embedding_service = EmbeddingService()
        self.chunking_service = ChunkingService()
        self.action_service = ActionService()
        self.classification_service = ClassificationService()
        self.duplicate_service = DuplicateService()
        self.version_service = VersionService()
        self.relationship_service = RelationshipService()
        self.db = firestore_db
        self.actions_collection = self.db.collection('actions')
        self.relationships_collection = self.db.collection('relationships')
        # We'll store duplicates and versions as relationships with specific types

    def process_document(self, document: Document, file_path: str) -> Document:
        """
        Process a document: extract text, generate embedding, extract actions, classify,
        and check for duplicates, versions, and relationships.
        """
        logger.info(f"Processing document {document.doc_id} for intelligence")

        # Step 1: Extract text
        document.extraction_status = "processing"
        extracted_text, extraction_status = self.extraction_service.extract_text(
            file_path, document.content_type, document.filename
        )

        if extraction_status == "success":
            document.extraction_status = "completed"
            logger.info(f"Text extraction successful for document {document.doc_id}")
        else:
            document.extraction_status = "failed"
            logger.warning(f"Text extraction failed for document {document.doc_id}")
            document.intelligence_status = "failed"
            # Save the document status updates
            self._save_document_status(document)
            return document

        # Step 2: Generate embedding
        document.intelligence_status = "processing"
        embedding = self.embedding_service.get_embedding(extracted_text)
        if embedding is not None:
            document.embedding = embedding.tolist()  # Convert numpy array to list for Firestore
            document.intelligence_status = "completed"
            logger.info(f"Embedding generated for document {document.doc_id}")
        else:
            document.intelligence_status = "failed"
            logger.warning(f"Embedding generation failed for document {document.doc_id}")
            self._save_document_status(document)
            return document

        # Step 3: Extract actions from the text
        actions = self.action_service.extract_actions(extracted_text)
        logger.info(f"Extracted {len(actions)} actions from document {document.doc_id}")
        # Store actions
        self._store_actions(document.doc_id, actions)

        # Step 4: Classify the document
        category, confidence = self.classification_service.classify(document, extracted_text)
        # We'll store the classification in the document itself (we could add a field, but for now we'll store in a separate collection or in the document)
        # Let's add a classification field to the document? We'll store it in a separate collection for simplicity.
        # We'll create a classification collection later. For now, we'll just log it.
        logger.info(f"Document {document.doc_id} classified as {category} with confidence {confidence}")

        # Step 5: Check for duplicates and versions (requires comparing with existing documents)
        # We'll fetch existing documents for the same owner (to limit scope)
        owner_id = document.owner_id
        existing_docs = self._get_existing_documents(owner_id, limit=100)  # Limit to recent 100 for performance
        logger.info(f"Checking against {len(existing_docs)} existing documents for owner {owner_id}")

        # Duplicate detection
        duplicates = self.duplicate_service.find_duplicates(document, existing_docs)
        if duplicates:
            logger.info(f"Found {len(duplicates)} potential duplicates for document {document.doc_id}")
            self._store_duplicates(document.doc_id, duplicates)

        # Version detection
        versions = self.version_service.find_possible_versions(document, existing_docs)
        if versions:
            logger.info(f"Found {len(versions)} potential versions for document {document.doc_id}")
            self._store_versions(document.doc_id, versions)

        # Relationship detection (general related documents)
        relationships = self.relationship_service.find_related_documents(document, existing_docs, threshold=0.6)
        if relationships:
            logger.info(f"Found {len(relationships)} potential relationships for document {document.doc_id}")
            self._store_relationships(document.doc_id, relationships, relationship_type='related')

        # Update the document in Firestore (to save embedding and intelligence status)
        self._save_document(document)

        return document

    def _save_document_status(self, document: Document):
        """
        Save only the extraction and intelligence status fields.
        """
        doc_ref = self.db.collection('documents').document(document.doc_id)
        doc_ref.update({
            'extraction_status': document.extraction_status,
            'intelligence_status': document.intelligence_status
        })

    def _save_document(self, document: Document):
        """
        Save the entire document (or at least the embedding and status).
        """
        doc_ref = self.db.collection('documents').document(document.doc_id)
        doc_ref.update({
            'embedding': document.embedding,
            'extraction_status': document.extraction_status,
            'intelligence_status': document.intelligence_status
        })

    def _get_existing_documents(self, owner_id: str, limit: int = 100) -> List[Document]:
        """
        Fetch existing documents for the given owner.
        """
        docs = []
        try:
            query = self.db.collection('documents').where('owner_id', '==', owner_id).limit(limit)
            for doc in query.stream():
                docs.append(Document.from_dict(doc.to_dict()))
        except Exception as e:
            logger.error(f"Error fetching existing documents: {e}")
        return docs

    def _store_actions(self, document_id: str, actions: List[Dict]):
        """
        Store extracted actions in the actions collection.
        """
        for action_dict in actions:
            action = Action(
                action_id=str(uuid.uuid4()),
                document_id=document_id,
                action_text=action_dict.get('action'),
                deadline=action_dict.get('deadline'),
                action_type=action_dict.get('type'),
                confidence=action_dict.get('confidence')
            )
            try:
                self.actions_collection.document(action.action_id).set(action.to_dict())
            except Exception as e:
                logger.error(f"Error storing action: {e}")

    def _store_duplicates(self, document_id: str, duplicates: List[Tuple[Document, float, str]]):
        """
        Store duplicate relationships.
        The type in the tuple is either 'exact' or 'near'.
        """
        for doc, confidence, dup_type in duplicates:
            relationship_type = 'exact_duplicate' if dup_type == 'exact' else 'near_duplicate'
            relationship = Relationship(
                relationship_id=str(uuid.uuid4()),
                source_document_id=document_id,
                target_document_id=doc.doc_id,
                relationship_type=relationship_type,
                confidence=confidence,
                reason=f"Detected as {dup_type} duplicate based on file hash and content similarity"
            )
            try:
                self.relationships_collection.document(relationship.relationship_id).set(relationship.to_dict())
            except Exception as e:
                logger.error(f"Error storing duplicate relationship: {e}")

    def _store_versions(self, document_id: str, versions: List[Tuple[Document, float, str]]):
        """
        Store version relationships.
        The type in the tuple is either 'possible_previous' or 'possible_newer'.
        """
        for doc, confidence, version_type in versions:
            relationship_type = 'possible_previous_version' if version_type == 'possible_previous' else 'possible_newer_version'
            relationship = Relationship(
                relationship_id=str(uuid.uuid4()),
                source_document_id=document_id,
                target_document_id=doc.doc_id,
                relationship_type=relationship_type,
                confidence=confidence,
                reason=f"Detected as {version_type} based on filename patterns, content similarity, and temporal closeness"
            )
            try:
                self.relationships_collection.document(relationship.relationship_id).set(relationship.to_dict())
            except Exception as e:
                logger.error(f"Error storing version relationship: {e}")

    def _store_relationships(self, document_id: str, relationships: List[Tuple[Document, float, str]], relationship_type: str = 'related'):
        """
        Store general relationships.
        """
        for doc, confidence, reason in relationships:
            relationship = Relationship(
                relationship_id=str(uuid.uuid4()),
                source_document_id=document_id,
                target_document_id=doc.doc_id,
                relationship_type=relationship_type,
                confidence=confidence,
                reason=reason
            )
            try:
                self.relationships_collection.document(relationship.relationship_id).set(relationship.to_dict())
            except Exception as e:
                logger.error(f"Error storing relationship: {e}")

    def get_document_intelligence(self, document_id: str) -> Dict:
        """
        Retrieve all intelligence data for a document: actions, classifications, relationships.
        """
        intelligence = {
            'actions': [],
            'relationships': [],
            'classification': None
        }
        # Get actions
        try:
            actions_query = self.actions_collection.where('document_id', '==', document_id)
            for action_doc in actions_query.stream():
                intelligence['actions'].append(Action.from_dict(action_doc.to_dict()).to_dict())
        except Exception as e:
            logger.error(f"Error fetching actions: {e}")

        # Get relationships (both directions)
        try:
            # As source
            rel_query1 = self.relationships_collection.where('source_document_id', '==', document_id)
            for rel_doc in rel_query1.stream():
                intelligence['relationships'].append(Relationship.from_dict(rel_doc.to_dict()).to_dict())
            # As target
            rel_query2 = self.relationships_collection.where('target_document_id', '==', document_id)
            for rel_doc in rel_query2.stream():
                intelligence['relationships'].append(Relationship.from_dict(rel_doc.to_dict()).to_dict())
        except Exception as e:
            logger.error(f"Error fetching relationships: {e}")

        # TODO: Fetch classification from a classification collection or from the document if we stored it there
        # For now, we'll leave it as None

        return intelligence