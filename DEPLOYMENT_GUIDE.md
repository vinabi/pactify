# 🚀 Pactify Contract Risk Analyzer - Deployment Guide

## 📋 **Complete System Overview**

You now have a **production-ready contract analysis pipeline** with:

✅ **5-Stage Automated Pipeline**
✅ **Email Integration (SendGrid)**  
✅ **Document Processing (PDF, DOCX, TXT)**
✅ **Risk Detection & Red Flags**
✅ **Template Comparison**
✅ **Executive Summaries**
✅ **Human-in-the-Loop Workflow**

---

## 🔧 **Setup Instructions**

### 1. **Environment Variables**
Create `.env` file:
```bash
# SendGrid (Required for email features)
SENDGRID_API_KEY=your_sendgrid_api_key
EMAIL_SENDER=contracts@yourcompany.com

# AI Models
GROQ_API_KEY=your_groq_api_key  # or OPENAI_API_KEY
MODEL_NAME=llama-3.1-70b-versatile

# DocuSign (Optional)
DOCUSIGN_INTEGRATION_KEY=your_integration_key
DOCUSIGN_USER_ID=your_user_id
```

### 2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3. **Start the API Server**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. **Start the UI (Optional)**
```bash
streamlit run app_ui/home.py --server.port 8501
```

---

## 📧 **Email-Driven Workflow**

### **Option A: Manual Email Processing**
Send contracts via API with email delivery:

```bash
curl -X POST "http://localhost:8000/review_pipeline" \
  -F "file=@contract.pdf" \
  -F "requester_email=legal@company.com" \
  -F "jurisdiction=California"
```

### **Option B: Automated Email Monitoring** 
For continuous email monitoring:

```python
# Create email_monitor_service.py
import asyncio
from agents.email_monitor import start_email_monitoring

if __name__ == "__main__":
    asyncio.run(start_email_monitoring())
```

Run with: `python email_monitor_service.py`

---

## 🎯 **Usage Examples**

### **1. Quick Contract Analysis**
```python
from agents.orchestrator import ContractOrchestrator

async def analyze_my_contract():
    orchestrator = ContractOrchestrator()
    
    with open("contract.pdf", "rb") as f:
        result = await orchestrator.process_contract(
            file_bytes=f.read(),
            filename="contract.pdf",
            requester_email="me@company.com"
        )
    
    print(f"Recommendation: {result.recommendation}")
    print(f"Risk Score: {result.risk_score}/100")
```

### **2. Batch Processing**
```python
import os
from pathlib import Path

async def process_contract_folder(folder_path: str):
    orchestrator = ContractOrchestrator()
    
    for file_path in Path(folder_path).glob("*.pdf"):
        with open(file_path, "rb") as f:
            result = await orchestrator.process_contract(
                file_bytes=f.read(),
                filename=file_path.name,
                requester_email="legal@company.com"
            )
        
        print(f"{file_path.name}: {result.recommendation}")
```

### **3. API Integration**
```javascript
// Frontend JavaScript example
async function analyzeContract(file, email) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('requester_email', email);
    
    const response = await fetch('/review_pipeline', {
        method: 'POST',
        body: formData
    });
    
    const result = await response.json();
    console.log(`${result.filename}: ${result.recommendation}`);
}
```

---

## 📊 **System Capabilities**

### **Contract Types Detected:**
- Non-Disclosure Agreements (NDAs)
- Service Agreements
- Employment Contracts
- License Agreements  
- Purchase Agreements
- Partnership Agreements
- Terms of Service

### **Risk Categories Identified:**
- **High Risk**: Unlimited liability, one-sided terms
- **Medium Risk**: Payment issues, unfavorable jurisdiction  
- **Low Risk**: Minor concerns, missing standard clauses

### **Output Formats:**
- **JSON API** responses
- **HTML email** summaries
- **Executive reports** for management
- **Redlined documents** with suggestions

---

## 🔒 **Security & Compliance**

### **Data Protection:**
- Documents processed in memory only
- No persistent storage of contract content
- Email delivery with encryption (SendGrid)
- Configurable retention policies

### **Access Control:**
- API key authentication
- Email domain validation
- Role-based permissions (coming soon)

---

## 📈 **Monitoring & Analytics**

### **Check System Stats:**
```bash
curl http://localhost:8000/pipeline_stats
```

### **Health Check:**
```bash
curl http://localhost:8000/healthz
```

---

## 🐳 **Docker Deployment**

### **Build and Run:**
```bash
# API Service
docker build -f ops/dockerfile.api -t pactify-api .
docker run -p 8000:8000 --env-file .env pactify-api

# UI Service  
docker build -f ops/dockerfile.ui -t pactify-ui .
docker run -p 8501:8501 pactify-ui

# Complete Stack
docker-compose -f ops/docker-compose.yml up -d
```

---

## 🔧 **Customization**

### **Add Custom Risk Rules:**
Edit `agents/contract_detector.py`:
```python
CUSTOM_RED_FLAGS = [
    {
        "label": "My Company Specific Risk",
        "pattern": r"\bspecific\s+risky\s+term\b",
        "severity": "high"
    }
]
```

### **Custom Email Templates:**
Modify `agents/orchestrator.py` in `_send_review_email()` method.

### **Template Library:**
Add contract templates to ChromaDB for better comparison.

---

## 🚨 **Troubleshooting**

### **Common Issues:**

1. **"SendGrid API key not set"**
   - Add `SENDGRID_API_KEY` to environment
   - Verify sender email is verified in SendGrid

2. **"Document processing failed"**
   - Ensure file is PDF/DOCX/TXT
   - Check file isn't password protected
   - Verify file size < 10MB

3. **"Email monitoring not working"**
   - Use app-specific password for Gmail
   - Enable IMAP access
   - Check firewall/network settings

### **Logs:**
Check logs in console output or configure loguru for file logging.

---

## 🎯 **Next Steps**

1. **Deploy to production** server
2. **Configure email monitoring** for your domain
3. **Customize risk rules** for your organization
4. **Set up legal team access** and training
5. **Monitor and optimize** based on usage patterns

---

## 📞 **Support**

- Check logs for detailed error messages
- Test with sample contracts first
- Start with manual API calls before automation
- Monitor processing stats regularly

**Your contract analysis pipeline is ready for production use!** 🚀
