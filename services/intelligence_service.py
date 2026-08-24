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
        # We'll add a classification field to the document? We'll store it in a separate collection for simplicity.
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
        This is a placeholder implementation that uses extractive summarization.
        In a real app, this would use an LLM for abstractive summarization.
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

            # Simple extractive summarization: take first few sentences
            # In a real implementation, we would use an LLM for better summarization
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
            return "Unable to generate summary"

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
        Answer a question about a document using its content.
        This is a more natural way to interact with documents.
        """
        try:
            # Get document
            doc_ref = self.db.collection('documents').document(document_id)
            doc_data = doc_ref.get()
            if not doc_data.exists:
                return {'answer': 'Document not found', 'confidence': 0.0}

            # Get actions first (high confidence matches)
            actions = []
            try:
                actions_query = self.actions_collection.where('document_id', '==', document_id)
                for action_doc in actions_query.stream():
                    actions.append(Action.from_dict(action_doc.to_dict()).to_dict())
            except Exception as e:
                logger.error(f"Error fetching actions for QA: {e}")

            # Simple keyword matching for actions
            question_lower = question.lower()
            question_words = set([word for word in question_lower.split() if len(word) > 3])
            for action in actions:
                action_text = action.get('action', '').lower()
                action_words = set([word for word in action_text.split() if len(word) > 3])
                # If there's significant word overlap, answer based on the action
                if question_words and action_words:
                    overlap = question_words.intersection(action_words)
                    if len(overlap) >= min(2, len(question_words) // 2):  # At least 2 words or half the question words
                        return {
                            'answer': f"Based on the document, you need to: {action.get('action')}",
                            'confidence': 0.8,
                            'source': 'action',
                            'action_id': action.get('action_id')
                        }

            # If no action match, look for relevant content in the extracted text
            extracted_text = self._get_extracted_text(document_id)
            if extracted_text:
                # Simple approach: find sentences that contain question words
                import re
                # Split into sentences
                sentences = re.split(r'[.!?]+', extracted_text)
                sentences = [s.strip() for s in sentences if s.strip()]

                # Score sentences based on question word overlap
                scored_sentences = []
                for sentence in sentences:
                    sentence_lower = sentence.lower()
                    sentence_words = set([word for word in sentence_lower.split() if len(word) > 3])
                    if sentence_words:
                        overlap = question_words.intersection(sentence_words)
                        if overlap:
                            # Score based on overlap ratio
                            score = len(overlap) / len(question_words)
                            scored_sentences.append((sentence, score))

                # Sort by score and take the best ones
                scored_sentences.sort(key=lambda x: x[1], reverse=True)
                top_sentences = scored_sentences[:3]  # Top 3 sentences

                if top_sentences:
                    # Combine the top sentences into an answer
                    answer_text = ' '.join([sent[0] for sent in top_sentences])
                    # Calculate average confidence
                    avg_confidence = sum([sent[1] for sent in top_sentences]) / len(top_sentences)
                    # Cap confidence at 0.9 since this is still a simple algorithm
                    confidence = min(0.9, avg_confidence)

                    return {
                        'answer': answer_text,
                        'confidence': confidence,
                        'source': 'extracted_text',
                        'sentences_used': len(top_sentences)
                    }

            # If we still don't have a good answer, return a placeholder
            return {
                'answer': f"I couldn't find specific information in the document to answer: '{question}'. The document has been processed and contains {len(extracted_text) if extracted_text else 0} characters of text, but I need more advanced AI capabilities to provide a detailed answer to this question.",
                'confidence': 0.3,
                'source': 'placeholder',
                'extracted_text_length': len(extracted_text) if extracted_text else 0
            }

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