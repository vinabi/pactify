# scripts/ingest_templates.py - CONTRACT TEMPLATE INGESTION SYSTEM
import os
from uuid import uuid4
from agents.tools_vector import get_chroma
from chromadb.utils import embedding_functions

CHROMA_DIR = os.environ.get("CHROMA_DIR", ".chroma")
TEMPLATES_COLLECTION = "contract_templates"

# Standard contract template clauses
STANDARD_TEMPLATES = {
    "Non-Disclosure Agreement": {
        "confidential_information_definition": """
        "Confidential Information" means any and all non-public, proprietary or confidential information, 
        technical data, trade secrets or know-how, including, but not limited to, research, product plans, 
        products, services, customers, customer lists, markets, software, developments, inventions, processes, 
        formulas, technology, designs, drawings, engineering, hardware configuration information, marketing, 
        finances or other business information disclosed by Company.
        """,
        "permitted_disclosures": """
        The obligations of confidentiality shall not apply to information that: (a) is or becomes generally 
        known to the public through no breach of this Agreement by the Receiving Party; (b) is rightfully 
        known by the Receiving Party prior to disclosure; (c) is rightfully received by the Receiving Party 
        from a third party without breach of any confidentiality obligation; (d) is independently developed 
        by the Receiving Party without use of Confidential Information; or (e) is required to be disclosed 
        by law or court order, provided that written notice is given to Company.
        """,
        "return_of_information": """
        Upon termination of this Agreement or upon Company's written request, Receiving Party shall 
        promptly return or destroy all documents, materials, and other tangible manifestations of 
        Confidential Information and all copies thereof in Receiving Party's possession or control.
        """,
        "term_duration": """
        This Agreement shall remain in effect for a period of five (5) years from the date first written 
        above, unless earlier terminated. The obligations of confidentiality shall survive termination 
        of this Agreement and continue for a period of five (5) years.
        """
    },
    
    "Service Agreement": {
        "scope_of_work": """
        Company shall provide the services described in Exhibit A attached hereto and incorporated by 
        reference ("Services"). Company shall perform the Services in a professional and workmanlike 
        manner in accordance with industry standards and the timeline set forth in Exhibit A.
        """,
        "payment_terms": """
        Client shall pay Company the fees set forth in Exhibit B. Unless otherwise specified, payment 
        terms are Net 30 days from invoice date. Late payments shall accrue interest at 1.5% per month 
        or the maximum rate permitted by law, whichever is less.
        """,
        "intellectual_property": """
        All work product, deliverables, inventions, and intellectual property created by Company in 
        the performance of Services shall be owned by Client. Company hereby assigns to Client all 
        right, title and interest in and to such work product, except for Company's pre-existing 
        intellectual property and general methodologies.
        """,
        "termination_rights": """
        Either party may terminate this Agreement: (a) for convenience with thirty (30) days prior 
        written notice; or (b) immediately for material breach if such breach is not cured within 
        ten (10) days after written notice.
        """,
        "liability_limitations": """
        EXCEPT FOR BREACHES OF CONFIDENTIALITY, IP INFRINGEMENT, OR DEATH/BODILY INJURY, EACH PARTY'S 
        TOTAL LIABILITY SHALL NOT EXCEED THE FEES PAID UNDER THIS AGREEMENT IN THE TWELVE (12) MONTHS 
        PRECEDING THE CLAIM. IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR INDIRECT, CONSEQUENTIAL, OR 
        PUNITIVE DAMAGES.
        """
    },
    
    "Employment Agreement": {
        "job_responsibilities": """
        Employee shall serve as [Title] and shall perform such duties and responsibilities as are 
        customarily associated with such position, as well as such other duties as may be assigned 
        by Company's management from time to time that are consistent with Employee's position, 
        qualifications, and experience.
        """,
        "compensation_benefits": """
        As compensation for services, Company shall pay Employee an annual salary of $[Amount] payable 
        in accordance with Company's standard payroll practices. Employee shall be eligible to participate 
        in Company's standard benefits programs, including health insurance, retirement plans, and paid 
        time off, subject to the terms and conditions of such programs.
        """,
        "termination_conditions": """
        Either party may terminate employment: (a) at any time with or without cause upon thirty (30) 
        days written notice; or (b) immediately for cause, including but not limited to misconduct, 
        breach of duties, or conviction of a felony. Upon termination, Employee shall receive earned 
        but unpaid salary through the termination date.
        """,
        "non_compete_clause": """
        During employment and for twelve (12) months thereafter, Employee shall not directly or indirectly 
        engage in any business that competes with Company's business within [Geographic Area]. This 
        restriction shall apply only to the specific business activities in which Employee was involved 
        during the final two years of employment.
        """,
        "confidentiality": """
        Employee acknowledges access to Company's confidential information and agrees to maintain 
        the confidentiality of such information during and after employment. Employee shall not 
        disclose, use, or exploit confidential information except as required for job performance.
        """
    },

    "License Agreement": {
        "grant_of_license": """
        Subject to the terms and conditions of this Agreement, Licensor hereby grants to Licensee a 
        non-exclusive, non-transferable license to use the Licensed Technology solely for Licensee's 
        internal business purposes during the term of this Agreement.
        """,
        "license_restrictions": """
        Licensee shall not: (a) modify, adapt, or create derivative works of the Licensed Technology; 
        (b) reverse engineer, disassemble, or decompile the Licensed Technology; (c) distribute, sublicense, 
        or transfer the Licensed Technology to any third party; or (d) remove any proprietary notices.
        """,
        "royalty_terms": """
        In consideration for the rights granted herein, Licensee shall pay Licensor a royalty equal to 
        [X]% of Net Sales of Licensed Products, payable quarterly within forty-five (45) days after 
        the end of each calendar quarter, together with a detailed royalty report.
        """,
        "ip_ownership": """
        Licensor retains all right, title, and interest in and to the Licensed Technology. No ownership 
        rights are transferred to Licensee. All improvements, modifications, or enhancements made by 
        Licensee shall become the property of Licensor.
        """
    },

    "Purchase Agreement": {
        "purchase_price": """
        The total purchase price for the goods/assets shall be $[Amount] ("Purchase Price"), payable 
        as follows: (a) $[Amount] upon execution of this Agreement; (b) $[Amount] upon delivery/closing; 
        and (c) the balance, if any, according to the payment schedule set forth in Exhibit A.
        """,
        "representations_warranties": """
        Seller represents and warrants that: (a) it has good and marketable title to the goods/assets; 
        (b) the goods/assets are free from liens and encumbrances; (c) it has full authority to enter 
        into this Agreement; and (d) the execution and performance of this Agreement will not violate 
        any other agreement or obligation.
        """,
        "closing_conditions": """
        The obligations of each party to consummate the purchase are subject to: (a) the accuracy of 
        representations and warranties; (b) performance of all covenants and agreements; (c) delivery 
        of required documents and certificates; and (d) satisfaction of conditions set forth in the 
        attached schedules.
        """,
        "risk_of_loss": """
        Risk of loss and title to goods shall pass to Buyer upon delivery to the designated location. 
        Seller shall bear all risk of loss or damage to goods until delivery. Buyer shall inspect goods 
        promptly and notify Seller of any defects within [X] days of delivery.
        """
    }
}

def create_templates_collection(client):
    """Create contract templates collection with proper embedding function"""
    try:
        # Try to get existing collection
        return client.get_collection(TEMPLATES_COLLECTION)
    except:
        # Create new collection
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        return client.create_collection(
            name=TEMPLATES_COLLECTION, 
            embedding_function=ef
        )

def ingest_standard_templates():
    """Ingest standard contract templates into ChromaDB"""
    vect = get_chroma(CHROMA_DIR)
    coll = create_templates_collection(vect)
    
    # Clear existing templates
    try:
        existing = coll.get()
        if existing['ids']:
            coll.delete(ids=existing['ids'])
            print(f"Cleared {len(existing['ids'])} existing templates")
    except:
        pass
    
    ids, documents, metadatas = [], [], []
    
    for contract_type, clauses in STANDARD_TEMPLATES.items():
        for clause_type, template_text in clauses.items():
            doc_id = str(uuid4())
            ids.append(doc_id)
            documents.append(template_text.strip())
            metadatas.append({
                "contract_type": contract_type,
                "clause_type": clause_type,
                "source": "standard_template",
                "risk_level": "low",  # Standard templates are low risk
                "quality": "high"
            })
    
    # Add some risky clause examples for comparison
    risky_clauses = {
        "Unlimited Liability": """
        Contractor shall indemnify, defend and hold harmless Company against any and all claims, 
        damages, losses, costs and expenses of any kind or nature whatsoever, including without 
        limitation attorneys' fees, arising out of or relating to this Agreement.
        """,
        "Broad IP Assignment": """
        Contractor hereby assigns to Company all inventions, discoveries, improvements, and works 
        of authorship conceived, made, or created by Contractor, whether or not related to the 
        services provided hereunder, during the term of this Agreement.
        """,
        "Perpetual Non-Compete": """
        Employee agrees that during employment and thereafter, Employee shall not directly or 
        indirectly engage in any business that competes with Company anywhere in the world.
        """,
        "One-sided Termination": """
        Company may terminate this Agreement at any time for any reason or no reason with immediate 
        effect. Contractor may not terminate this Agreement except for Company's material breach 
        that remains uncured for ninety (90) days after written notice.
        """
    }
    
    for clause_type, risky_text in risky_clauses.items():
        doc_id = str(uuid4())
        ids.append(doc_id)
        documents.append(risky_text.strip())
        metadatas.append({
            "contract_type": "Anti-Pattern",
            "clause_type": clause_type,
            "source": "risky_example", 
            "risk_level": "high",
            "quality": "poor"
        })
    
    # Ingest all templates
    coll.add(ids=ids, documents=documents, metadatas=metadatas)
    
    print(f"""
Template Ingestion Complete! 
- {len(STANDARD_TEMPLATES)} contract types ingested
- {sum(len(clauses) for clauses in STANDARD_TEMPLATES.values())} standard clause templates
- {len(risky_clauses)} risky clause examples
- Total: {len(ids)} templates in ChromaDB collection '{TEMPLATES_COLLECTION}'

Contract types available:
{chr(10).join('- ' + ct for ct in STANDARD_TEMPLATES.keys())}
    """)

def test_template_retrieval():
    """Test template retrieval functionality"""
    from agents.tools_vector import retrieve_snippets
    
    vect = get_chroma(CHROMA_DIR)
    
    test_clauses = [
        "The contractor shall indemnify the company against all claims",
        "Confidential information means proprietary data", 
        "Payment shall be made within thirty days",
        "Employee may not compete with the company"
    ]
    
    print("\n=== Template Retrieval Test ===")
    for test_clause in test_clauses:
        print(f"\nQuery: {test_clause}")
        try:
            matches = retrieve_snippets(vect, TEMPLATES_COLLECTION, test_clause, k=2)
            for meta, doc in matches:
                print(f"  → {meta.get('contract_type')} - {meta.get('clause_type')} ({meta.get('risk_level')})")
                print(f"    {doc[:100]}...")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    print("🚀 Ingesting Contract Templates...")
    ingest_standard_templates()
    test_template_retrieval()
    print("\n✅ Template system ready!")