# agents/override_handler.py - USER OVERRIDE FOR BORDERLINE DOCUMENTS
from __future__ import annotations
from typing import Dict, Any, List
from loguru import logger

class DocumentOverrideHandler:
    """Handle user overrides when system is uncertain about document type"""
    
    def __init__(self):
        self.override_log = []
    
    def should_offer_override(self, detection_details: Dict[str, Any]) -> bool:
        """Determine if user override option should be offered"""
        
        score = detection_details.get('score', 0)
        confidence = detection_details.get('confidence', 'minimal')
        
        # Offer override for borderline cases
        borderline_conditions = [
            score > -50 and score < 30,  # Borderline score
            confidence in ['minimal', 'low'],  # Low confidence
            'unknown' in detection_details.get('detected_type', ''),  # Unknown type
        ]
        
        return any(borderline_conditions)
    
    def get_override_options(self, text: str, filename: str) -> List[Dict[str, str]]:
        """Get override options for user to choose from"""
        
        text_lower = text.lower()
        options = []
        
        # Analyze content to suggest override types
        if any(word in text_lower for word in ['employment', 'employee', 'work', 'job', 'salary']):
            options.append({
                'type': 'employment_agreement',
                'label': 'Employment Agreement',
                'description': 'Analyze as employment contract'
            })
        
        if any(word in text_lower for word in ['confidential', 'nda', 'disclosure', 'proprietary']):
            options.append({
                'type': 'nda',
                'label': 'Non-Disclosure Agreement', 
                'description': 'Analyze as confidentiality agreement'
            })
        
        if any(word in text_lower for word in ['service', 'consulting', 'work', 'deliverable']):
            options.append({
                'type': 'service_agreement',
                'label': 'Service Agreement',
                'description': 'Analyze as service contract'
            })
        
        if any(word in text_lower for word in ['form', 'application', 'petition', 'government']):
            options.append({
                'type': 'legal_form',
                'label': 'Legal Form/Application',
                'description': 'Analyze as official legal document'
            })
        
        # Always offer general analysis
        options.append({
            'type': 'general_legal',
            'label': 'General Legal Document',
            'description': 'Analyze for general legal risks and improvements'
        })
        
        return options[:4]  # Max 4 options
    
    def log_override(self, filename: str, original_decision: str, override_choice: str, user_email: str):
        """Log user override for future system improvement"""
        
        override_entry = {
            'filename': filename,
            'original_decision': original_decision,
            'override_choice': override_choice,
            'user_email': user_email,
            'timestamp': 'now'  # Would use datetime in production
        }
        
        self.override_log.append(override_entry)
        logger.info(f"User override logged: {filename} → {override_choice}")
    
    def get_override_statistics(self) -> Dict[str, Any]:
        """Get statistics about user overrides for system improvement"""
        
        if not self.override_log:
            return {"total_overrides": 0}
        
        # Analyze override patterns
        override_types = [entry['override_choice'] for entry in self.override_log]
        most_common = max(set(override_types), key=override_types.count) if override_types else None
        
        return {
            "total_overrides": len(self.override_log),
            "most_common_override": most_common,
            "improvement_needed": len(self.override_log) > 10  # If many overrides, improve detection
        }

# Global instance
override_handler = DocumentOverrideHandler()
