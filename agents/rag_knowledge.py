# agents/rag_knowledge.py - RAG SYSTEM FOR RISK RULES KNOWLEDGE BASE
from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
from loguru import logger

class RiskRulesRAG:
    """RAG system for risk rules knowledge base"""
    
    def __init__(self, rules_file: str = "knowledge/risk_rules.md"):
        self.rules_file = rules_file
        self.rule_chunks = []
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Load and chunk the risk rules knowledge base"""
        try:
            rules_path = Path(self.rules_file)
            if not rules_path.exists():
                logger.warning(f"Risk rules file not found: {self.rules_file}")
                return
            
            content = rules_path.read_text(encoding='utf-8')
            self.rule_chunks = self.chunk_risk_rules(content)
            logger.info(f"Loaded {len(self.rule_chunks)} risk rule chunks")
            
        except Exception as e:
            logger.error(f"Failed to load risk rules: {e}")
            self.rule_chunks = []
    
    def chunk_risk_rules(self, content: str) -> List[Dict[str, Any]]:
        """Parse and chunk the risk rules markdown file"""
        chunks = []
        
        # Split by main sections
        sections = re.split(r'\n#+\s+', content)
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.split('\n')
            section_title = lines[0].strip()
            section_content = '\n'.join(lines[1:]).strip()
            
            if len(section_content) < 50:  # Skip tiny sections
                continue
            
            # Extract risk level if present
            risk_level = "medium"
            if any(word in section_title.lower() for word in ["high", "critical", "severe"]):
                risk_level = "high"
            elif any(word in section_title.lower() for word in ["low", "minor", "basic"]):
                risk_level = "low"
            
            # Extract category from section title
            category = self.extract_category(section_title)
            
            # Create chunk
            chunk = {
                "title": section_title,
                "content": section_content,
                "risk_level": risk_level,
                "category": category,
                "keywords": self.extract_keywords(section_content),
                "chunk_id": f"rule_{len(chunks)}"
            }
            
            chunks.append(chunk)
            
            # Further split long sections into sub-chunks
            if len(section_content) > 1000:
                sub_chunks = self.split_long_section(chunk)
                chunks.extend(sub_chunks)
        
        return chunks
    
    def extract_category(self, title: str) -> str:
        """Extract risk category from section title"""
        title_lower = title.lower()
        
        category_mapping = {
            'liability': ['liability', 'indemnity', 'damages', 'losses'],
            'payment': ['payment', 'invoice', 'billing', 'fees', 'cost'],
            'termination': ['termination', 'cancellation', 'end', 'expire'],
            'intellectual_property': ['ip', 'intellectual property', 'copyright', 'patent', 'trademark'],
            'confidentiality': ['confidential', 'nda', 'disclosure', 'proprietary', 'secret'],
            'jurisdiction': ['jurisdiction', 'governing law', 'court', 'venue'],
            'compliance': ['compliance', 'regulatory', 'legal', 'audit'],
            'force_majeure': ['force majeure', 'act of god', 'unforeseeable'],
            'warranty': ['warranty', 'guarantee', 'representation'],
            'assignment': ['assignment', 'transfer', 'successor']
        }
        
        for category, keywords in category_mapping.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
        
        return 'general'
    
    def extract_keywords(self, content: str) -> List[str]:
        """Extract key terms from content"""
        # Common legal/contract keywords to look for
        legal_terms = [
            'liability', 'indemnify', 'breach', 'damages', 'terminate', 'clause',
            'agreement', 'contract', 'party', 'obligation', 'warranty', 'represent',
            'confidential', 'proprietary', 'jurisdiction', 'governing law', 'dispute',
            'payment', 'invoice', 'fees', 'intellectual property', 'assignment',
            'force majeure', 'compliance', 'audit', 'penalty', 'liquidated damages'
        ]
        
        content_lower = content.lower()
        found_keywords = []
        
        for term in legal_terms:
            if term in content_lower:
                found_keywords.append(term)
        
        return found_keywords[:10]  # Top 10 keywords
    
    def split_long_section(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split long sections into smaller chunks"""
        content = chunk["content"]
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        sub_chunks = []
        current_chunk = ""
        
        for i, paragraph in enumerate(paragraphs):
            if len(current_chunk + paragraph) > 500 and current_chunk:
                # Create sub-chunk
                sub_chunk = {
                    **chunk,
                    "content": current_chunk.strip(),
                    "chunk_id": f"{chunk['chunk_id']}_sub_{len(sub_chunks)}",
                    "title": f"{chunk['title']} (Part {len(sub_chunks) + 1})"
                }
                sub_chunks.append(sub_chunk)
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        # Add remaining content
        if current_chunk.strip():
            sub_chunk = {
                **chunk,
                "content": current_chunk.strip(),
                "chunk_id": f"{chunk['chunk_id']}_sub_{len(sub_chunks)}",
                "title": f"{chunk['title']} (Part {len(sub_chunks) + 1})"
            }
            sub_chunks.append(sub_chunk)
        
        return sub_chunks
    
    def retrieve_relevant_rules(self, contract_text: str, query_type: str = "general", top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve most relevant risk rules for given contract text"""
        if not self.rule_chunks:
            logger.warning("No risk rules loaded")
            return []
        
        contract_lower = contract_text.lower()
        scored_chunks = []
        
        for chunk in self.rule_chunks:
            score = self.calculate_relevance_score(chunk, contract_lower, query_type)
            if score > 0:
                scored_chunks.append((score, chunk))
        
        # Sort by relevance score and return top_k
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for score, chunk in scored_chunks[:top_k]]
    
    def calculate_relevance_score(self, chunk: Dict[str, Any], contract_text: str, query_type: str) -> float:
        """Calculate relevance score between rule chunk and contract"""
        score = 0.0
        
        # Category match bonus
        if query_type == chunk["category"]:
            score += 2.0
        
        # Keyword matching
        keyword_matches = 0
        for keyword in chunk["keywords"]:
            if keyword in contract_text:
                keyword_matches += 1
                score += 1.0
        
        # Content similarity (simple approach)
        chunk_content_lower = chunk["content"].lower()
        common_phrases = [
            "unlimited liability", "indemnification", "governing law", "termination",
            "confidential information", "intellectual property", "payment terms",
            "force majeure", "dispute resolution", "warranty", "assignment"
        ]
        
        for phrase in common_phrases:
            if phrase in contract_text and phrase in chunk_content_lower:
                score += 1.5
        
        # Risk level relevance
        if chunk["risk_level"] == "high":
            score += 0.5  # Slightly prioritize high-risk rules
        
        # Length penalty for very short chunks
        if len(chunk["content"]) < 100:
            score *= 0.8
        
        return score
    
    def get_enhanced_analysis_prompt(self, contract_text: str, base_prompt: str) -> str:
        """Enhance analysis prompt with relevant risk rules"""
        relevant_rules = self.retrieve_relevant_rules(contract_text, top_k=3)
        
        if not relevant_rules:
            return base_prompt
        
        # Build enhanced prompt with RAG context
        rag_context = "\n\nRELEVANT RISK ANALYSIS GUIDELINES:\n"
        
        for i, rule in enumerate(relevant_rules, 1):
            rag_context += f"\n{i}. {rule['title']} (Risk Level: {rule['risk_level'].upper()})\n"
            rag_context += f"   {rule['content'][:300]}{'...' if len(rule['content']) > 300 else ''}\n"
        
        enhanced_prompt = base_prompt + rag_context + "\n\nApply these guidelines when analyzing the contract clauses."
        
        return enhanced_prompt
    
    def get_risk_recommendations(self, detected_risks: List[Dict[str, Any]]) -> List[str]:
        """Get specific recommendations based on detected risks"""
        recommendations = []
        
        for risk in detected_risks[:5]:  # Top 5 risks
            risk_category = risk.get('category', 'general')
            relevant_rules = self.retrieve_relevant_rules(
                f"{risk_category} {risk.get('label', '')}",
                query_type=risk_category,
                top_k=2
            )
            
            for rule in relevant_rules:
                if 'recommend' in rule['content'].lower() or 'should' in rule['content'].lower():
                    # Extract recommendation from rule content
                    sentences = rule['content'].split('.')
                    for sentence in sentences:
                        if any(word in sentence.lower() for word in ['recommend', 'should', 'consider', 'ensure']):
                            clean_sentence = sentence.strip()
                            if clean_sentence and len(clean_sentence) > 20:
                                recommendations.append(clean_sentence)
                                break
        
        return list(set(recommendations))[:5]  # Remove duplicates, max 5

# Global instance
risk_rules_rag = RiskRulesRAG()
