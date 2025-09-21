# 🚀 Complete Deployment Guide - GitHub & Hugging Face

## ✅ **Errors Fixed**

- ✅ **Streamlit import error** - Fixed `from dashboard import main` → `from app_ui.dashboard import main`
- ✅ **File read error** - Fixed attachment reading in email function
- ✅ **Missing dependencies** - Updated requirements.txt with all needed packages

---

## 📁 **Exact Repository Structure**

### **For Both GitHub & Hugging Face:**

```
pactify/
├── README.md                    # Project documentation
├── requirements.txt             # All dependencies (unified)
├── .gitignore                  # Git ignore rules
├── app.py                      # 🎯 Hugging Face entry point  
├── streamlit_app.py            # 🎯 Streamlit Cloud entry point
├── .streamlit/
│   └── config.toml             # Streamlit configuration
├── agents/
│   ├── contract_detector.py   # Smart contract detection
│   ├── rag_knowledge.py       # RAG system for risk rules
│   ├── orchestrator.py        # Main pipeline orchestrator
│   ├── email_monitor.py       # Email monitoring (optional)
│   ├── pipeline.py            # Analysis pipeline
│   ├── prompts.py             # AI prompts
│   ├── schemas.py             # Data models
│   ├── tools_email.py         # SendGrid integration
│   ├── tools_parser.py        # Document parsing
│   ├── tools_vector.py        # Vector operations
│   └── tools_docusign.py      # DocuSign (optional)
├── api/
│   ├── main.py                # FastAPI backend
│   ├── models.py              # API models
│   ├── settings.py            # Configuration
│   └── utils.py               # Utilities
├── app_ui/
│   ├── dashboard.py           # 🎯 Main Streamlit dashboard
│   └── home.py                # Alternative UI (optional)
├── knowledge/
│   └── risk_rules.md          # 🧠 AI knowledge base
├── ops/
│   ├── docker-compose.yml     # Docker deployment
│   ├── dockerfile.api         # API container
│   └── dockerfile.ui          # UI container
├── scripts/
│   └── ingest_risks.py        # Knowledge base setup
└── tests/
    ├── sample_contracts/
    │   └── tiny_nda.txt       # Test files
    └── test_api.py            # API tests
```

---

## 🔐 **Required Secrets/Environment Variables**

### **Minimum Required (For Basic Functionality):**
```bash
SENDGRID_API_KEY=SG.your_sendgrid_api_key_here
EMAIL_SENDER=contracts@yourdomain.com
GROQ_API_KEY=gsk_your_groq_api_key_here
MODEL_NAME=llama-3.1-70b-versatile
```

### **Optional (Enhanced Features):**
```bash
OPENAI_API_KEY=sk-your_openai_key_here
DOCUSIGN_INTEGRATION_KEY=your_docusign_key
DOCUSIGN_USER_ID=your_docusign_user_id
```

---

## 🐙 **GitHub Deployment**

### **1. Repository Setup**
```bash
# Create and push repository
git init
git add .
git commit -m "Initial commit: Pactify Contract Analyzer"
git branch -M main
git remote add origin https://github.com/yourusername/pactify.git
git push -u origin main
```

### **2. GitHub Secrets (For Actions)**
In GitHub Settings > Secrets and variables > Actions:
```
SENDGRID_API_KEY = SG.your_key_here
EMAIL_SENDER = contracts@yourdomain.com  
GROQ_API_KEY = gsk_your_key_here
MODEL_NAME = llama-3.1-70b-versatile
```

### **3. Repository Settings**
- ✅ **Public repository** (for easy access)
- ✅ **Include README.md** (comprehensive documentation)
- ✅ **Add .gitignore** (Python template + custom rules)
- ✅ **Topics**: Add tags like `contract-analysis`, `ai`, `streamlit`, `legal-tech`

---

## 🤗 **Hugging Face Spaces Deployment**

### **1. Create New Space**
1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. **Space name**: `pactify-contract-analyzer`
3. **SDK**: Select **Streamlit**
4. **Hardware**: CPU Basic (free) or CPU Upgrade ($7/month)
5. **Visibility**: Public
6. Click **Create Space**

### **2. Upload Files Method A - Web Interface**
Upload these files directly:
```
✅ app.py                    # Main entry point
✅ requirements.txt          # Dependencies  
✅ README.md                # Documentation
✅ agents/ (entire folder)   # AI engines
✅ app_ui/ (entire folder)   # UI components
✅ knowledge/ (entire folder) # Knowledge base
✅ .streamlit/config.toml    # Streamlit config
```

### **3. Upload Files Method B - Git**
```bash
# Clone your HF space
git clone https://huggingface.co/spaces/yourusername/pactify-contract-analyzer
cd pactify-contract-analyzer

# Copy files from your project
cp -r /path/to/your/pactify/* .

# Push to HF
git add .
git commit -m "Deploy Pactify Contract Analyzer"
git push
```

### **4. Hugging Face Secrets**
In your Space Settings > Variables and secrets:

**Repository secrets:**
```
SENDGRID_API_KEY = SG.your_sendgrid_api_key_here
EMAIL_SENDER = contracts@yourdomain.com
GROQ_API_KEY = gsk_your_groq_api_key_here  
MODEL_NAME = llama-3.1-70b-versatile
```

### **5. Space Configuration**
Create `requirements.txt` (already done) with all dependencies:
- Streamlit will automatically install from `requirements.txt`
- HF Spaces will use `app.py` as the entry point
- Secrets are automatically injected as environment variables

---

## 🌐 **Streamlit Cloud Deployment**

### **1. Connect Repository**
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect GitHub account
3. Select your `pactify` repository
4. Main file: `streamlit_app.py`
5. Requirements: `requirements.txt`

### **2. Streamlit Secrets**
In your Streamlit Cloud app settings, add:
```toml
[secrets]
SENDGRID_API_KEY = "SG.your_sendgrid_api_key_here"
EMAIL_SENDER = "contracts@yourdomain.com"
GROQ_API_KEY = "gsk_your_groq_api_key_here"
MODEL_NAME = "llama-3.1-70b-versatile"
```

---

## 🔧 **Platform-Specific Entry Points**

### **Hugging Face Spaces**
- Uses: `app.py` 
- Purpose: HF Spaces looks for this file automatically

### **Streamlit Cloud**  
- Uses: `streamlit_app.py`
- Purpose: Traditional Streamlit deployment entry point

### **Local Development**
- Uses: Either file works
- Run: `streamlit run app.py` OR `streamlit run streamlit_app.py`

---

## ✅ **Deployment Checklist**

### **Pre-Deployment**
- [ ] All secrets obtained (SendGrid, Groq, Email)
- [ ] Repository structure matches above
- [ ] README.md is complete
- [ ] requirements.txt includes all dependencies
- [ ] .gitignore excludes sensitive files

### **GitHub**
- [ ] Repository created and pushed
- [ ] Secrets added to GitHub Actions
- [ ] Repository is public
- [ ] Topics/tags added

### **Hugging Face**
- [ ] Space created with Streamlit SDK
- [ ] All files uploaded
- [ ] Secrets configured in Space settings
- [ ] Space is building successfully

### **Streamlit Cloud**
- [ ] Repository connected
- [ ] Main file set to `streamlit_app.py`
- [ ] Secrets configured in Streamlit settings
- [ ] App deployed successfully

---

## 🎯 **Success URLs**

After deployment, your apps will be available at:

- **Hugging Face**: `https://huggingface.co/spaces/yourusername/pactify-contract-analyzer`
- **Streamlit Cloud**: `https://yourusername-pactify-streamlit-app-xyz123.streamlit.app`
- **GitHub**: `https://github.com/yourusername/pactify`

---

## 🔍 **Troubleshooting**

### **Common Issues:**
1. **Import errors**: Ensure file structure matches exactly
2. **Missing secrets**: Verify all environment variables are set
3. **Dependency issues**: Check requirements.txt has all packages
4. **Email failures**: Verify SendGrid API key and sender email

### **Logs:**
- **HF Spaces**: Check build logs in your space
- **Streamlit Cloud**: View logs in app settings
- **GitHub**: Check Actions tab for any CI/CD issues

**Your deployment is now complete and ready for production!** 🚀
