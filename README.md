# AI-Consulting – FastAPI Demo

Lightweight FastAPI app with:
- 📁 **File upload** panel  
- 🤖 **Chatbot** panel (wired for OpenAI GPT)  
- ⚡ No database required

## 🚀 Quick start

```bash
# 1. Clone
git clone https://github.com/<your-user>/<repo>.git
cd ai-consulting

# 2. Create & activate virtualenv (Python 3.9+)
python3 -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate

# 3. Install deps
pip install -r requirements.txt

# 4. Set your OpenAI key (optional until you wire `/chat`)
export OPENAI_API_KEY=sk-...

# 5. Run dev server
uvicorn app.main:app --reload
# open http://127.0.0.1:8000  ➜  see UI
