import re
from typing import Dict, List, Any

class EntityExtractionService:
    """
    Service for extracting structured entities (dates, money, emails, phones, orgs) 
    from unstructured document text using regex and heuristics.
    """
    
    def __init__(self):
        # Regex patterns
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'\b(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\b')
        
        # Money patterns: $100, $100.00, 100 USD, 1,000.00
        self.money_pattern = re.compile(r'(?:[$€£₹]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|INR))')
        
        # Date patterns: YYYY-MM-DD, MM/DD/YYYY, DD-MM-YYYY, Jan 1, 2020, etc.
        self.date_pattern = re.compile(r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b')
        
        # Simple heuristic for Organizations/Names: Consecutive capitalized words (ignoring starting words of sentences if possible, but keeping it simple)
        self.org_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extracts various entities from the given text.
        Returns a dictionary with keys: emails, phones, money, dates, organizations
        """
        if not text or not isinstance(text, str):
            return {
                "emails": [],
                "phones": [],
                "money": [],
                "dates": [],
                "organizations": []
            }
            
        # Clean text slightly to improve matching
        clean_text = re.sub(r'\s+', ' ', text)
        
        emails = list(set(self.email_pattern.findall(clean_text)))
        
        # Extract phones and reconstruct them nicely
        raw_phones = self.phone_pattern.findall(clean_text)
        phones = []
        for p in raw_phones:
            # p is a tuple from the capture groups
            phone_str = "-".join([g for g in p[1:4] if g])
            if p[0]: # Country code
                phone_str = f"+{p[0]} {phone_str}"
            if p[4]: # Extension
                phone_str = f"{phone_str} x{p[4]}"
            if phone_str:
                phones.append(phone_str)
        phones = list(set(phones))
        
        money = list(set(self.money_pattern.findall(clean_text)))
        dates = list(set(self.date_pattern.findall(clean_text)))
        
        # Organizations heuristic
        raw_orgs = self.org_pattern.findall(clean_text)
        
        # Filter out common false positives (e.g., at start of sentences)
        filtered_orgs = []
        common_words = {'The', 'This', 'That', 'These', 'Those', 'It', 'He', 'She', 'They', 'We', 'In', 'On', 'At', 'To', 'For', 'With', 'By'}
        for org in raw_orgs:
            first_word = org.split()[0]
            if first_word not in common_words and len(org) > 4:
                filtered_orgs.append(org)
                
        organizations = list(set(filtered_orgs))
        
        return {
            "emails": emails,
            "phones": phones,
            "money": money,
            "dates": dates,
            "organizations": organizations
        }
