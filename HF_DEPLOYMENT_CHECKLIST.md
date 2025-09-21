# 🤗 Hugging Face Spaces Deployment Checklist

## 📋 **Pre-Deployment Checklist**

### **✅ Files Required for HF Spaces:**
- [x] `app.py` - Main entry point for HF
- [x] `Dockerfile` - Container configuration  
- [x] `.dockerignore` - Build optimization
- [x] `requirements.txt` - Dependencies
- [x] `README.md` - Space documentation (rename README_HF.md)
- [x] `agents/` - AI analysis engine
- [x] `app_ui/` - Streamlit interface
- [x] `knowledge/` - RAG knowledge base
- [x] `.streamlit/config.toml` - Streamlit config

### **✅ Environment Variables for HF Spaces:**
```bash
SENDGRID_API_KEY=SG.your_sendgrid_api_key_here
EMAIL_SENDER=contracts@yourdomain.com
GROQ_API_KEY=gsk_your_groq_api_key_here
MODEL_NAME=llama-3.1-70b-versatile
```

---

## 🚀 **Hugging Face Deployment Steps**

### **Step 1: Create HF Space**
1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. **Space name**: `pactify-contract-analyzer` 
3. **SDK**: Select **Docker** (not Streamlit, since we have custom Dockerfile)
4. **Hardware**: 
   - **CPU Basic** (free) - sufficient for most use
   - **CPU Upgrade** ($7/month) - faster processing
5. **Visibility**: Public or Private
6. Click **Create Space**

### **Step 2: Upload Files**

**Method A - Web Interface:**
1. Upload `Dockerfile` first
2. Upload `app.py`
3. Upload `requirements.txt`
4. Upload `README_HF.md` as `README.md`
5. Upload all folders: `agents/`, `app_ui/`, `knowledge/`, `.streamlit/`

**Method B - Git Clone:**
```bash
# Clone your HF space
git clone https://huggingface.co/spaces/yourusername/pactify-contract-analyzer
cd pactify-contract-analyzer

# Copy files from your project (exclude unnecessary files)
cp /path/to/pactify/app.py .
cp /path/to/pactify/Dockerfile .
cp /path/to/pactify/requirements.txt .
cp /path/to/pactify/README_HF.md README.md
cp -r /path/to/pactify/agents .
cp -r /path/to/pactify/app_ui .
cp -r /path/to/pactify/knowledge .
cp -r /path/to/pactify/.streamlit .

# Push to HF
git add .
git commit -m "Deploy Pactify Contract Analyzer"
git push
```

### **Step 3: Configure Environment Variables**
1. Go to your Space Settings
2. Click **Variables and secrets**
3. Add each environment variable:
   ```
   SENDGRID_API_KEY = SG.your_actual_api_key
   EMAIL_SENDER = your_verified_email@domain.com
   GROQ_API_KEY = gsk_your_actual_groq_key
   MODEL_NAME = llama-3.1-70b-versatile
   ```

### **Step 4: Monitor Deployment**
1. **Build logs**: Watch the Docker build process
2. **Runtime logs**: Monitor for any startup issues
3. **Space status**: Should show "Running" when ready
4. **Test upload**: Try with a sample contract

---

## 🐳 **Docker Configuration Details**

### **Base Image**: `python:3.11-slim`
- Lightweight and fast
- Python 3.11 for best compatibility
- Sufficient for Streamlit and AI libraries

### **Port**: `7860` 
- Standard port for HF Spaces
- Automatically exposed and routed

### **Optimizations:**
- **Multi-stage copying** for better caching
- **Minimal system packages** for faster builds
- **Health checks** for reliability
- **Proper cleanup** to reduce image size

---

## 🔧 **Troubleshooting**

### **Common Issues:**

**1. Build Fails**
- Check Dockerfile syntax
- Verify requirements.txt has correct package names
- Monitor build logs for specific errors

**2. App Won't Start**
- Check if port 7860 is properly exposed
- Verify app.py imports work correctly
- Check environment variables are set

**3. Import Errors**
- Ensure all folders (agents, app_ui, knowledge) are uploaded
- Check file structure matches exactly
- Verify Python path configuration

**4. Email Not Working**
- Verify SendGrid API key is valid
- Check EMAIL_SENDER is verified in SendGrid
- Test with a simple contract first

### **Debug Commands:**
```bash
# Local Docker test
docker build -t pactify-test .
docker run -p 7860:7860 pactify-test

# Check logs
docker logs container_id
```

---

## 🎯 **Expected Build Time**

- **Dependencies install**: ~3-5 minutes
- **Application copy**: ~30 seconds  
- **Total build time**: ~5-8 minutes
- **Startup time**: ~30 seconds

---

## ✅ **Success Indicators**

### **Deployment Successful When:**
- ✅ Build completes without errors
- ✅ Space shows "Running" status
- ✅ App accessible at space URL
- ✅ File upload works
- ✅ Analysis cards display properly
- ✅ Email delivery works (with valid API keys)

### **Test with Sample Contract:**
1. Upload any PDF/TXT contract
2. Enter your email
3. Click "Start Analysis"
4. Verify cards populate with risk percentages
5. Check email for professional report

---

## 🎉 **Your HF Space Will Be:**
`https://huggingface.co/spaces/yourusername/pactify-contract-analyzer`

**Professional, fast, and ready for production use!** 🚀
