import logging
import uuid
from datetime import datetime, timedelta, timezone
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
        # Lazy initialization of heavy services
        self._llm_service = None
        self._embedding_service = None
        self.chunking_service = ChunkingService()
        self.action_service = ActionService()
        self.classification_service = ClassificationService()
        self.duplicate_service = DuplicateService()
        self.version_service = VersionService()
        self.relationship_service = RelationshipService()
        self.db = firestore_db
        self.actions_collection = self.db.collection('actions')
        self.relationships_collection = self.db.collection('relationships')
        # Collection for storing extracted text (with TTL via timestamp)
        self.extracted_texts_collection = self.db.collection('extracted_texts')
        # We'll store duplicates and versions as relationships with specific types

    @property
    def embedding_service(self):
        """Lazy load the embedding service to avoid loading the model at startup."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    @property
    def llm_service(self):
        """Lazy load the LLM service to avoid loading the model at startup."""
        if self._llm_service is None:
            from services.llm_service import LLMService
            self._llm_service = LLMService()
        return self._llm_service

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
            # Store the extracted text for later use (with timestamp for potential TTL)
            self._store_extracted_text(document.doc_id, extracted_text)

            # Step 2.5: Generate LLM-based summary and key points
            logger.info(f"Generating LLM-based summary and key points for document {document.doc_id}")
            try:
                # Generate abstractive summary using LLM service
                if self.llm_service.is_available():
                    llm_summary = self.llm_service.generate_summary(extracted_text, max_length=200)
                    if llm_summary and llm_summary.strip():
                        document.llm_summary = llm_summary.strip()
                        logger.info(f"Generated LLM summary for document {document.doc_id}: {llm_summary[:50]}...")
                
                # Extract key points using LLM service
                if self.llm_service.is_available():
                    key_points = self.llm_service.extract_key_points(extracted_text, num_points=5)
                    if key_points:
                        document.llm_key_points = key_points
                        logger.info(f"Extracted {len(key_points)} key points for document {document.doc_id}")
            except Exception as e:
                logger.warning(f"LLM processing failed for document {document.doc_id}: {e}")
                # Continue with processing even if LLM fails
        else:
            document.extraction_status = "failed"
            logger.warning(f"Text extraction failed for document {document.doc_id}")
            document.intelligence_status = "failed"
            # Save the document status updates
            self._save_document_status(document)
            return document

        # Step 2: Generate embedding
        document.intelligence_status = "processing"
        embedding = self.embedding_service.generate_embedding(extracted_text)
        if embedding is not None:
            document.embedding = embedding  # Already a list
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
        document.document_type = category
        document.classification_confidence = confidence
        logger.info(f"Document {document.doc_id} classified as {category} with confidence {confidence}")

        # Step 4.5: Extract entities and generate AI suggestions
        try:
            from services.entity_extraction_service import EntityExtractionService
            entity_extractor = EntityExtractionService()
            entities_dict = entity_extractor.extract_entities(extracted_text)
            
            # Save raw entities list
            all_entities = []
            for k, v in entities_dict.items():
                if v:
                    all_entities.extend(v)
            document.entities = list(set(all_entities))[:15] # keep top 15

            # Set a suggested title if none exists
            if document.filename:
                import os
                base_name = os.path.splitext(document.filename)[0]
                document.suggested_title = f"{category.capitalize()} - {base_name}"
            
            document.suggested_tags = [category] + entities_dict.get('organizations', [])[:3]
            document.suggestions_status = 'pending'
            
        except Exception as e:
            logger.warning(f"Entity extraction failed for document {document.doc_id}: {e}")

        # Step 4.6: Classify sensitivity level
        try:
            sensitivity = self.classification_service.classify_sensitivity(extracted_text)
            document.sensitivity_level = sensitivity
            logger.info(f"Document {document.doc_id} sensitivity: {sensitivity}")
        except Exception as e:
            logger.warning(f"Sensitivity classification failed for document {document.doc_id}: {e}")

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

        document.processing_status = 'completed'
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

    def _store_extracted_text(self, document_id: str, text: str):
        """
        Store extracted text for a document in a separate collection.
        Includes a timestamp that can be used for TTL-style cleanup.
        """
        try:
            text_doc = {
                'document_id': document_id,
                'text': text,
                'created_at': datetime.now(timezone.utc),
                # In a production app, you would set up TTL on this field
                # to automatically delete documents after a certain time
                # For now, we'll rely on manual cleanup or assume text is needed
                # as long as the document exists
            }
            # Use the document_id as the document ID in the extracted_texts collection
            # for easy lookup
            self.extracted_texts_collection.document(document_id).set(text_doc)
            logger.info(f"Stored extracted text for document {document_id}")
        except Exception as e:
            logger.error(f"Error storing extracted text for document {document_id}: {e}")

    def _get_extracted_text(self, document_id: str) -> Optional[str]:
        """
        Retrieve extracted text for a document.
        Returns None if not found.
        """
        try:
            text_doc = self.extracted_texts_collection.document(document_id).get()
            if text_doc.exists:
                return text_doc.to_dict().get('text')
            return None
        except Exception as e:
            logger.error(f"Error retrieving extracted text for document {document_id}: {e}")
            return None

    def _get_existing_documents(self, owner_id: str, limit: int = 50) -> List[Document]:
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

    def summarize_document(self, document_id: str) -> str:
        """
        Generate a summary of the document using its extracted text.
        Uses LLM service for abstractive summarization with extractive fallback.
        """
        try:
            # Get document metadata
            doc_ref = self.db.collection('documents').document(document_id)
            doc_data = doc_ref.get()
            if not doc_data.exists:
                return "Document not found"

            # Convert to dictionary for consistent access
            doc_dict = doc_data.to_dict()

            # Get the extracted text
            extracted_text = self._get_extracted_text(document_id)
            if not extracted_text:
                # Fall back to placeholder if no extracted text is available
                return f"Summary of {doc_dict.get('filename', 'document')}: This document contains important information that has been processed by our AI system. Key topics include document processing, information extraction, and intelligent document management."

            # Try to use LLM service for summarization
            if self.llm_service.is_available():
                try:
                    # Generate summary using LLM service
                    llm_summary = self.llm_service.generate_summary(extracted_text, max_length=200)
                    if llm_summary and llm_summary.strip():
                        return f"Summary of {doc_dict.get('filename', 'document')}: {llm_summary}"
                except Exception as e:
                    logger.warning(f"LLM summarization failed, falling back to extractive: {e}")
            
            # Fallback to extractive summarization
            import re
            # Split into sentences (simple approach)
            sentences = re.split(r'[.!?]+', extracted_text)
            sentences = [s.strip() for s in sentences if s.strip()]

            # Take first 3 sentences or fewer if there aren't that many
            summary_sentences = sentences[:3]
            summary = '. '.join(summary_sentences)
            if summary and not summary.endswith('.'):
                summary += '.'

            return f"Summary of {doc_dict.get('filename', 'document')}: {summary}"
        except Exception as e:
            logger.error(f"Error summarizing document {document_id}: {e}")
            return "Unable to generate summary due to an error."
    def extract_key_points(self, document_id: str, num_points: int = 5) -> List[str]:
        """
        Extract key bullet points from the document using the LLM service.
        Returns a list of strings (each string is a bullet point).
        """
        try:
            # Get document metadata
            doc_ref = self.db.collection('documents').document(document_id)
            doc_data = doc_ref.get()
            if not doc_data.exists:
                return []

            # Convert to dictionary for consistent access
            doc_dict = doc_data.to_dict()

            # Get the extracted text
            extracted_text = self._get_extracted_text(document_id)
            if not extracted_text:
                return []

            # Try to use LLM service for key point extraction
            if self.llm_service.is_available():
                try:
                    # Extract key points using LLM service
                    key_points = self.llm_service.extract_key_points(extracted_text, num_points)
                    if key_points:
                        return key_points
                except Exception as e:
                    logger.warning(f"LLM key point extraction failed, falling back to empty: {e}")
            
            # Fallback to empty list (we could implement extractive key point extraction here,
            # but for simplicity we'll return empty if LLM is not available)
            return []
        except Exception as e:
            logger.error(f"Error extracting key points from document {document_id}: {e}")
            return []
    def semantic_search(self, query: str, owner_id: str, limit: int = 10) -> List[Dict]:
        """
        Perform semantic search on documents using embeddings.
        """
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_service.generate_embedding(query)
            if query_embedding is None:
                return []

            # Get documents for the owner
            docs = self._get_existing_documents(owner_id, limit=100)  # Get more docs to search through

            # Calculate similarities
            results = []
            for doc in docs:
                if doc.embedding:
                    # Calculate cosine similarity
                    similarity = np.dot(query_embedding, doc.embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(doc.embedding))
                    results.append({
                        'document': doc,
                        'similarity': float(similarity)
                    })

            # Sort by similarity and return top results
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:limit]
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []

    def get_document_insights(self, document_id: str) -> Dict:
        """
        Generate insights for a document.
        """
        try:
            # Get document
            doc_ref = self.db.collection('documents').document(document_id)
            doc_data = doc_ref.get()
            if not doc_data.exists:
                return {}

            doc = Document.from_dict(doc_data.to_dict())

            # Get extracted text for insights
            extracted_text = self._get_extracted_text(document_id)

            # Generate insights
            insights = {
                'summary': self.summarize_document(document_id),
                'word_count': len(extracted_text.split()) if extracted_text else 0,
                'character_count': len(extracted_text) if extracted_text else 0,
                'processing_time': 'N/A',  # In a real app, we would track this
                'key_topics': self._extract_key_topics(extracted_text) if extracted_text else ['Document Processing', 'Information Extraction', 'AI Analysis'],
                'readability_score': self._calculate_readability_score(extracted_text) if extracted_text else 8.5,
                'sentiment': self._analyze_sentiment(extracted_text) if extracted_text else 'neutral',
                'language': self._detect_language(extracted_text) if extracted_text else 'en'
            }

            return insights
        except Exception as e:
            logger.error(f"Error generating insights for document {document_id}: {e}")
            return {}

    def _extract_key_topics(self, text: str) -> List[str]:
        """
        Extract key topics from text using simple keyword frequency.
        In a real implementation, we would use NLP techniques like TF-IDF or entity extraction.
        """
        if not text:
            return []

        try:
            import re
            from collections import Counter

            # Simple approach: get word frequencies, filter out common words
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())

            # Common English stop words to filter out
            stop_words = {'that', 'this', 'with', 'from', 'they', 'know', 'have', 'been', 'will',
                         'would', 'there', 'their', 'what', 'which', 'when', 'where', 'who',
                         'how', 'been', 'have', 'has', 'had', 'but', 'not', 'are', 'was', 'were',
                         'been', 'have', 'has', 'had', 'having', 'does', 'did', 'doing', 'done'}

            # Filter out stop words and count frequencies
            filtered_words = [word for word in words if word not in stop_words]
            word_counts = Counter(filtered_words)

            # Get top 5 most common words
            top_words = [word for word, count in word_counts.most_common(5)]

            # Return as topics (capitalized)
            return [word.title() for word in top_words]
        except Exception as e:
            logger.error(f"Error extracting key topics: {e}")
            return ['Document Processing', 'Information Extraction', 'AI Analysis']

    def _calculate_readability_score(self, text: str) -> float:
        """
        Calculate a simple readability score.
        In a real implementation, we would use established metrics like Flesch-Kincaid.
        """
        if not text:
            return 8.5  # Default middle score

        try:
            import re
            # Simple approximation based on sentence length and word length
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            if not sentences:
                return 8.5

            words = re.findall(r'\b[a-zA-Z]+\b', text)
            if not words:
                return 8.5

            avg_sentence_length = len(words) / len(sentences)
            avg_word_length = sum(len(word) for word in words) / len(words)

            # Simple heuristic: lower scores for longer sentences and words
            # This is a very rough approximation
            score = max(0, min(10, 12 - (avg_sentence_length * 0.1) - (avg_word_length * 0.2)))
            return round(score, 1)
        except Exception as e:
            logger.error(f"Error calculating readability score: {e}")
            return 8.5

    def _analyze_sentiment(self, text: str) -> str:
        """
        Analyze sentiment of text.
        In a real implementation, we would use NLP sentiment analysis.
        """
        if not text:
            return 'neutral'

        try:
            import re
            # Very simple sentiment analysis based on keyword matching
            positive_words = {'good', 'great', 'excellent', 'positive', 'happy', 'benefit',
                             'advantage', 'success', 'effective', 'working', 'improve',
                             'improvement', 'increase', 'growth', 'win', 'victory'}
            negative_words = {'bad', 'terrible', 'awful', 'negative', 'sad', 'problem',
                             'issue', 'fail', 'failure', 'broken', 'decrease', 'decline',
                             'loss', 'damage', 'harm', 'issue', 'trouble', 'difficult'}

            words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
            if not words:
                return 'neutral'

            positive_count = sum(1 for word in words if word in positive_words)
            negative_count = sum(1 for word in words if word in negative_words)

            if positive_count > negative_count * 1.5:
                return 'positive'
            elif negative_count > positive_count * 1.5:
                return 'negative'
            else:
                return 'neutral'
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return 'neutral'

    def _detect_language(self, text: str) -> str:
        """
        Detect language of text.
        In a real implementation, we would use a language detection library.
        """
        if not text:
            return 'en'

        try:
            import re
            # Very simple language detection based on common words
            # This is just a placeholder - in reality we'd use langdetect or similar
            common_english = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i'}
            words = set(re.findall(r'\b[a-zA-Z]{2,}\b', text.lower()))
            if not words:
                return 'en'

            # Calculate percentage of common English words
            common_count = sum(1 for word in words if word in common_english)
            if len(words) > 0:
                english_ratio = common_count / len(words)
                if english_ratio > 0.3:  # Arbitrary threshold
                    return 'en'

            # Default to English if we can't determine
            return 'en'
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return 'en'

    def ask_document_question(self, document_id: str, question: str) -> Dict:
        """
        Answer a question about a document using its content with RAG+LLM approach.
        This retrieves relevant chunks from the document and uses an LLM to answer based on the context.
        """
        try:
            # Get document metadata
            doc_ref = self.db.collection('documents').document(document_id)
            doc_data = doc_ref.get()
            if not doc_data.exists:
                return {'answer': 'Document not found', 'confidence': 0.0}

            # Convert to dictionary for consistent access
            doc_dict = doc_data.to_dict()

            # Get the extracted text
            extracted_text = self._get_extracted_text(document_id)
            if not extracted_text:
                return {
                    'answer': 'No text content found in the document to answer questions.',
                    'confidence': 0.0,
                    'source': 'no_text'
                }

            # If question is empty, return early
            if not question or not question.strip():
                return {
                    'answer': 'Please provide a question to answer.',
                    'confidence': 0.0,
                    'source': 'invalid_question'
                }

            # Chunk the text if it's too long
            # We'll use chunks of 1000 characters with 200 character overlap
            max_chunk_size = 1000
            overlap_size = 200
            
            chunks = []
            if len(extracted_text) <= max_chunk_size:
                # Text is short enough, use as single chunk
                chunks = [extracted_text]
            else:
                # Split into overlapping chunks
                start = 0
                while start < len(extracted_text):
                    end = start + max_chunk_size
                    chunk = extracted_text[start:end]
                    chunks.append(chunk)
                    start = end - overlap_size  # Move start back by overlap for next chunk
                    if start >= len(extracted_text):
                        break

            # Generate embedding for the question
            question_embedding = self.embedding_service.generate_embedding(question)
            if question_embedding is None:
                return {
                    'answer': 'Unable to process the question due to embedding generation failure.',
                    'confidence': 0.0,
                    'source': 'embedding_error'
                }

            # Generate embeddings for all chunks and compute similarities
            chunk_embeddings = []
            valid_chunks = []
            
            for i, chunk in enumerate(chunks):
                if not chunk or not chunk.strip():
                    continue
                    
                chunk_embedding = self.embedding_service.generate_embedding(chunk)
                if chunk_embedding is not None:
                    chunk_embeddings.append(chunk_embedding)
                    valid_chunks.append(chunk)
                else:
                    logger.warning(f"Failed to generate embedding for chunk {i}")

            if not chunk_embeddings:
                return {
                    'answer': 'Unable to process document text due to embedding generation failure.',
                    'confidence': 0.0,
                    'source': 'chunk_embedding_error'
                }

            # Compute similarities between question and chunks
            import numpy as np
            similarities = []
            for chunk_embedding in chunk_embeddings:
                # Cosine similarity
                similarity = np.dot(question_embedding, chunk_embedding) / (
                    np.linalg.norm(question_embedding) * np.linalg.norm(chunk_embedding)
                )
                similarities.append(similarity)

            # Get top N chunks (we'll use top 3 or fewer if we have fewer chunks)
            top_n = min(3, len(similarities))
            if top_n == 0:
                return {
                    'answer': 'Unable to find relevant content in the document to answer the question.',
                    'confidence': 0.0,
                    'source': 'no_similarity'
                }

            # Get indices of top similarities
            top_indices = np.argsort(similarities)[-top_n:][::-1]  # Descending order
            
            # Get the selected chunks
            selected_chunks = [valid_chunks[i] for i in top_indices]
            selected_similarities = [similarities[i] for i in top_indices]
            
            # Combine selected chunks into context
            context = "\n\n---\n\n".join(selected_chunks)
            
            # Use LLM service to answer the question based on context
            llm_response = self.llm_service.answer_question(context, question)
            
            # Format the response
            answer = llm_response.get('answer', 'Unable to generate an answer.')
            confidence = llm_response.get('confidence', 0.5)
            
            # Add source information
            result = {
                'answer': answer,
                'confidence': confidence,
                'source': 'rag_llm',
                'context_chunks_used': len(selected_chunks),
                'context_similarities': [float(s) for s in selected_similarities]  # Convert to float for JSON serialization
            }
            
            return result

        except Exception as e:
            logger.error(f"Error answering question about document {document_id}: {e}")
            return {'answer': 'Error processing question', 'confidence': 0.0}
    def cleanup_old_extracted_text(self, max_age_hours: int = 24) -> int:
        """
        Clean up extracted text older than the specified age.
        This helps prevent storage from growing indefinitely.
        Returns the number of documents deleted.
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

            # Query for old extracted text documents
            old_texts = self.extracted_texts_collection.where('created_at', '<', cutoff_time).stream()

            deleted_count = 0
            for text_doc in old_texts:
                try:
                    text_doc.reference.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting old extracted text {text_doc.id}: {e}")

            logger.info(f"Cleaned up {deleted_count} old extracted text documents older than {max_age_hours} hours")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old extracted text: {e}")
            return 0