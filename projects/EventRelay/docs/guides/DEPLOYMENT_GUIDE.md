# 🚀 PRODUCTION DEPLOYMENT GUIDE
## Fly.io (Backend) + Vercel (Frontend)

---

## 📋 **PREREQUISITES**

### **Required Accounts:**
- [ ] **Fly.io Account**: https://fly.io (Free tier available)
- [ ] **Vercel Account**: https://vercel.com (Free tier available)
- [ ] **GitHub Account**: For repository hosting

### **Required Tools:**
- [ ] **Fly CLI**: `curl -L https://fly.io/install.sh | sh`
- [ ] **Vercel CLI**: `npm i -g vercel`
- [ ] **Docker**: For local testing (optional)

---

## 🎯 **STEP 1: BACKEND DEPLOYMENT (Fly.io)**

### **1.1 Install Fly CLI**
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
fly auth login
```

### **1.2 Deploy Backend**
```bash
# Navigate to project directory
cd /Users/garvey/Desktop/youtube_extension

# Run deployment script
./deploy-fly.sh
```

### **1.3 Verify Backend Deployment**
```bash
# Check app status
fly status

# Test health endpoint
curl https://youtube-extension-api.fly.dev/health

# View logs
fly logs
```

### **1.4 Set Environment Variables**
```bash
# Set all required API keys
fly secrets set \
  YOUTUBE_API_KEY="your_youtube_api_key" \
  GEMINI_API_KEY="your_gemini_api_key" \
  XAI_GROK4_API="your_grok4_api_key" \
  OPENAI_API_KEY="your_openai_api_key" \
  ANTHROPIC_API_KEY="your_anthropic_api_key" \
  ASSEMBLYAI_API_KEY="your_assemblyai_api_key"
```

---

## 🎯 **STEP 2: FRONTEND DEPLOYMENT (Vercel)**

### **2.1 Install Vercel CLI**
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login
```

### **2.2 Deploy Frontend**
```bash
# Navigate to frontend directory
cd frontend

# Deploy to Vercel
vercel --prod
```

### **2.3 Configure Environment Variables**
```bash
# Set frontend environment variables
vercel env add REACT_APP_API_URL
vercel env add REACT_APP_WS_URL
vercel env add REACT_APP_MCP_SERVER_URL

# Values to set:
# REACT_APP_API_URL: https://youtube-extension-api.fly.dev
# REACT_APP_WS_URL: wss://youtube-extension-api.fly.dev/ws
# REACT_APP_MCP_SERVER_URL: https://youtube-extension-api.fly.dev
```

---

## 🎯 **STEP 3: INTEGRATION TESTING**

### **3.1 Test Backend Endpoints**
```bash
# Health check
curl https://youtube-extension-api.fly.dev/health

# Chat endpoint
curl -X POST https://youtube-extension-api.fly.dev/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test"}'

# Video processing
curl -X POST https://youtube-extension-api.fly.dev/api/process-video \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=aircAruvnKk"}'
```

### **3.2 Test Frontend**
- [ ] Visit your Vercel deployment URL
- [ ] Test chat functionality
- [ ] Test video processing
- [ ] Test WebSocket connections

---

## 🎯 **STEP 4: MONITORING & MAINTENANCE**

### **4.1 Fly.io Monitoring**
```bash
# View app metrics
fly status

# View logs
fly logs

# Scale app if needed
fly scale count 2
```

### **4.2 Vercel Monitoring**
- [ ] Visit Vercel dashboard
- [ ] Check deployment status
- [ ] Monitor performance
- [ ] View analytics

---

## 🔧 **TROUBLESHOOTING**

### **Common Issues:**

**Backend Issues:**
```bash
# Check app status
fly status

# View logs
fly logs

# Restart app
fly apps restart youtube-extension-api

# Check environment variables
fly secrets list
```

**Frontend Issues:**
```bash
# Redeploy frontend
cd frontend && vercel --prod

# Check environment variables
vercel env ls
```

**Connection Issues:**
- [ ] Verify CORS configuration
- [ ] Check WebSocket URL format
- [ ] Validate API endpoints

---

## 📊 **PERFORMANCE OPTIMIZATION**

### **Backend (Fly.io):**
- [ ] Enable auto-scaling
- [ ] Monitor memory usage
- [ ] Optimize Docker image
- [ ] Use persistent volumes for data

### **Frontend (Vercel):**
- [ ] Enable CDN caching
- [ ] Optimize bundle size
- [ ] Use edge functions
- [ ] Enable compression

---

## 🔒 **SECURITY CHECKLIST**

### **Backend Security:**
- [x] Environment variables secured
- [x] SSL/HTTPS enabled
- [x] CORS properly configured
- [x] API keys not exposed

### **Frontend Security:**
- [x] Environment variables secured
- [x] SSL/HTTPS enabled
- [x] Security headers configured
- [x] No sensitive data in client

---

## 📈 **SUCCESS METRICS**

### **Technical Metrics:**
- [ ] Backend response time < 2 seconds
- [ ] Frontend load time < 3 seconds
- [ ] 99.9% uptime
- [ ] < 1% error rate

### **Business Metrics:**
- [ ] Video processing success rate > 95%
- [ ] User engagement metrics
- [ ] Feature usage tracking
- [ ] Performance monitoring

---

## 🎯 **NEXT STEPS**

After successful deployment:

1. **Set up custom domain** (optional)
2. **Configure monitoring alerts**
3. **Set up CI/CD pipeline**
4. **Implement backup strategies**
5. **Plan scaling strategy**

---

## 📞 **SUPPORT**

### **Fly.io Support:**
- Documentation: https://fly.io/docs/
- Community: https://community.fly.io/
- Status: https://status.fly.io/

### **Vercel Support:**
- Documentation: https://vercel.com/docs
- Community: https://github.com/vercel/vercel/discussions
- Status: https://vercel-status.com/

---

**🎉 CONGRATULATIONS!** Your YouTube Extension is now deployed to production!
