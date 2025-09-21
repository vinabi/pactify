#!/usr/bin/env python3
"""
Test script for the complete Pactify contract analysis pipeline
Run: python test_pipeline.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from agents.orchestrator import ContractOrchestrator

async def test_basic_pipeline():
    """Test the basic pipeline with sample contract"""
    print("🧪 Testing Pactify Contract Analysis Pipeline")
    print("=" * 50)
    
    # Initialize orchestrator
    orchestrator = ContractOrchestrator()
    
    # Test with sample contract text (simulating a simple NDA)
    sample_contract = """
NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of [DATE], by and between [COMPANY A] ("Disclosing Party") and [COMPANY B] ("Receiving Party").

WHEREAS, the Disclosing Party wishes to share certain confidential information with the Receiving Party;

NOW, THEREFORE, in consideration of the mutual covenants contained herein, the parties agree as follows:

1. CONFIDENTIAL INFORMATION
"Confidential Information" means any and all non-public, confidential or proprietary information disclosed by the Disclosing Party to the Receiving Party.

2. OBLIGATIONS
The Receiving Party agrees to:
(a) Hold all Confidential Information in strict confidence;
(b) Not disclose any Confidential Information to third parties without written consent;
(c) Use Confidential Information solely for evaluation purposes.

3. INDEMNIFICATION
Receiving Party shall indemnify and hold harmless Disclosing Party against all claims, damages, and expenses of any nature whatsoever arising from any breach of this Agreement.

4. GOVERNING LAW
This Agreement shall be governed by the laws of Delaware.

5. TERM
This Agreement shall remain in effect for a period of five (5) years from the date hereof.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.
"""
    
    try:
        # Convert to bytes (simulating file upload)
        contract_bytes = sample_contract.encode('utf-8')
        
        print("📄 Processing sample NDA contract...")
        
        # Run the complete pipeline
        result = await orchestrator.process_contract(
            file_bytes=contract_bytes,
            filename="sample_nda.txt",
            requester_email=None,  # Skip email for test
            jurisdiction="Delaware",
            strict_mode=True
        )
        
        # Display results
        print(f"\n✅ ANALYSIS COMPLETE")
        print(f"Document ID: {result.document_id}")
        print(f"Contract Type: {result.contract_type}")
        print(f"Risk Score: {result.risk_score}/100")
        print(f"Recommendation: {result.recommendation}")
        print(f"Processing Time: {result.processing_time_seconds:.2f}s")
        
        print(f"\n🚨 CRITICAL ISSUES ({len(result.critical_issues)}):")
        for issue in result.critical_issues[:3]:
            print(f"  • {issue}")
        
        print(f"\n📋 NEXT STEPS:")
        for i, step in enumerate(result.next_steps, 1):
            print(f"  {i}. {step}")
        
        print(f"\n🎯 EXECUTIVE SUMMARY:")
        print(result.executive_summary)
        
        # Test stats
        stats = orchestrator.get_stats()
        print(f"\n📊 PROCESSING STATS:")
        print(f"  • Processed: {stats['processed_contracts']}")
        print(f"  • Success Rate: {stats['success_rate']:.1%}")
        
        print(f"\n🎉 TEST COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False

def test_contract_detection():
    """Test contract detection capabilities"""
    print("\n🔍 Testing Contract Detection")
    print("-" * 30)
    
    from agents.contract_detector import looks_like_contract_v2
    
    test_cases = [
        ("Valid Contract", "This Service Agreement is entered into between Company A and Company B for the provision of consulting services. The parties agree as follows: 1. Scope of Work..."),
        ("Blog Post", "Welcome to our blog! Today we're discussing the latest trends in technology and how they impact our daily lives. Here are 5 key points..."),
        ("Email", "Hi John, Hope you're doing well. Can we schedule a meeting for next week to discuss the project timeline? Let me know your availability. Thanks, Sarah")
    ]
    
    for name, text in test_cases:
        is_contract, details = looks_like_contract_v2(text)
        print(f"  {name}: {'✅ Contract' if is_contract else '❌ Not Contract'} (Score: {details.get('score', 0)})")

def test_red_flags():
    """Test red flag detection"""
    print("\n🚩 Testing Red Flag Detection")
    print("-" * 30)
    
    from agents.contract_detector import find_red_flags
    
    risky_text = """
The Contractor shall indemnify Company against all claims and damages without limitation.
Payment terms are NET 90 days. This agreement automatically renews for 3 years.
All intellectual property created shall belong to Company. Governing law is Delaware.
Contractor may not compete for 24 months after termination in any jurisdiction.
"""
    
    red_flags = find_red_flags(risky_text)
    print(f"  Detected {len(red_flags)} red flags:")
    for flag in red_flags[:5]:  # Show top 5
        print(f"    • {flag.get('severity', 'unknown').upper()}: {flag.get('label', 'Unknown issue')}")

if __name__ == "__main__":
    print("🚀 PACTIFY CONTRACT ANALYSIS SYSTEM TEST")
    print("=" * 60)
    
    # Run basic tests
    test_contract_detection()
    test_red_flags()
    
    # Run full pipeline test
    print("\n" + "=" * 60)
    success = asyncio.run(test_basic_pipeline())
    
    if success:
        print("\n🎉 ALL TESTS PASSED - SYSTEM READY FOR DEPLOYMENT!")
    else:
        print("\n❌ TESTS FAILED - CHECK CONFIGURATION")
        sys.exit(1)
