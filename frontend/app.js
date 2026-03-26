// ===== NyayaBot Frontend Application =====
// Policy-to-Citizen RAG Chatbot

const POLICIES_DB = [
  { id: 1, icon: "🌾", name: "PM-KISAN", ministry: "Ministry of Agriculture", category: "agriculture", desc: "Provides ₹6,000/year income support to small and marginal farmers owning up to 2 hectares of land.", tags: ["₹6,000/year", "Farmers", "Direct Benefit Transfer"], benefit: true },
  { id: 2, icon: "🏠", name: "PM Awas Yojana (Urban)", ministry: "MoHUA", category: "housing", desc: "Affordable housing scheme for EWS, LIG, and MIG beneficiaries in urban areas through CLSS subsidy.", tags: ["₹2.67 lakh subsidy", "Urban", "Housing"], benefit: true },
  { id: 3, icon: "🏡", name: "PM Awas Yojana (Rural)", ministry: "Ministry of Rural Development", category: "housing", desc: "Provides financial assistance of ₹1.20 lakh (plain) or ₹1.30 lakh (hilly) to homeless in rural areas.", tags: ["₹1.20-1.30 lakh", "Rural", "Housing"], benefit: true },
  { id: 4, icon: "🏥", name: "Ayushman Bharat PM-JAY", ministry: "MoHFW", category: "health", desc: "Health cover of ₹5 lakh per family per year for secondary and tertiary hospitalization for bottom 40% families.", tags: ["₹5 lakh cover", "Health Insurance", "Cashless"], benefit: true },
  { id: 5, icon: "👷", name: "MGNREGA", ministry: "Ministry of Rural Development", category: "employment", desc: "Guarantees 100 days of wage employment per year to rural households whose adult members do unskilled manual work.", tags: ["100 days/year", "Rural", "Employment"], benefit: true },
  { id: 6, icon: "🔥", name: "PM Ujjwala Yojana", ministry: "Ministry of Petroleum", category: "women", desc: "Provides free LPG connections to women from BPL households to reduce dependence on conventional cooking fuels.", tags: ["Free LPG", "BPL Women", "Clean Energy"], benefit: true },
  { id: 7, icon: "🏦", name: "Jan Dhan Yojana", ministry: "Ministry of Finance", category: "finance", desc: "Universal banking access providing zero-balance savings accounts with ₹1 lakh accident insurance and ₹30,000 life cover.", tags: ["Zero Balance", "₹1 lakh insurance", "Banking"], benefit: true },
  { id: 8, icon: "👧", name: "Sukanya Samriddhi Yojana", ministry: "Ministry of Finance", category: "women", desc: "Savings scheme for girl children offering 8.2% interest rate with tax benefits under Section 80C.", tags: ["8.2% interest", "Girl Child", "Tax Benefit"], benefit: true },
  { id: 9, icon: "📚", name: "PM Scholarship Scheme", ministry: "Ministry of Education", category: "education", desc: "Scholarships for children of ex-servicemen for studying professional courses with ₹2,500/month for boys and ₹3,000/month for girls.", tags: ["₹3,000/month", "Education", "Ex-Servicemen"], benefit: true },
  { id: 10, icon: "🌊", name: "PM KUSUM", ministry: "MNRE", category: "agriculture", desc: "Provides solar pumps and grid-connected solar power plants to farmers to reduce electricity bills and provide additional income.", tags: ["Solar Energy", "Farmers", "60% subsidy"], benefit: true },
  { id: 11, icon: "👨‍💼", name: "PM Mudra Yojana", ministry: "Ministry of Finance", category: "employment", desc: "Provides loans up to ₹10 lakh to non-corporate, non-farm small/micro enterprises through Shishu, Kishore, and Tarun categories.", tags: ["Up to ₹10 lakh", "MSME", "Loan"], benefit: true },
  { id: 12, icon: "🍽", name: "PM Garib Kalyan Anna Yojana", ministry: "Ministry of Food", category: "health", desc: "Free food grains – 5 kg rice/wheat per person per month to approximately 81 crore beneficiaries under NFSA.", tags: ["Free Food", "5 kg/month", "NFSA"], benefit: true },
];

const SCHEME_KNOWLEDGE = {
  "PM-KISAN": {
    eligibility: "Small and marginal farmers with less than 2 hectares of cultivable land. Excludes institutional land holders, former/present government employees, income tax payers.",
    benefits: "₹6,000 per year in 3 equal installments of ₹2,000 directly to bank account.",
    how_to_apply: "1. Visit pmkisan.gov.in\n2. Click 'Farmer Corner' > 'New Farmer Registration'\n3. Enter Aadhaar number, mobile, state\n4. Fill land details from land records\n5. Submit — verification happens via state government",
    documents: "Aadhaar card, Bank passbook, Land records (Khasra/Khatauni), Mobile number linked to Aadhaar",
    helpline: "PM-KISAN helpline: 155261 | 011-24300606"
  },
  "Ayushman Bharat": {
    eligibility: "SECC 2011 data-based. Covers bottom 40% families. Deprivation and occupational criteria for rural/urban. Check at pmjay.gov.in or call 14555.",
    benefits: "₹5 lakh health cover per family/year. Covers pre & post hospitalization. 1,929 medical procedures. No cap on family size.",
    how_to_apply: "1. Check eligibility at pmjay.gov.in or call 14555\n2. Visit empanelled hospital\n3. Show Aadhaar/ration card to Ayushman Mitra\n4. Get AB-PMJAY card\n5. Treatment is cashless",
    documents: "Aadhaar card OR Ration card + any government photo ID",
    helpline: "Ayushman Bharat helpline: 14555 (toll free)"
  },
  "PM Awas Yojana": {
    eligibility: "Urban: EWS (income <₹3L), LIG (₹3-6L), MIG-I (₹6-12L), MIG-II (₹12-18L). Should not own a pucca house.",
    benefits: "Interest subsidy of 6.5% for EWS/LIG on loans up to ₹6 lakh. MIG-I: 4% on ₹9 lakh. MIG-II: 3% on ₹12 lakh.",
    how_to_apply: "1. Apply at pmaymis.gov.in\n2. Or visit nearest Common Service Centre (CSC)\n3. Fill online application with Aadhaar\n4. Submit income certificate and property documents\n5. Subsidy directly credited to loan account",
    documents: "Aadhaar, Income certificate, Property documents, Bank account, Caste certificate (if applicable)",
    helpline: "PMAY helpline: 1800-11-3377 (toll free)"
  },
  "MGNREGA": {
    eligibility: "Any adult member of rural household willing to do unskilled manual work. Must register and get Job Card.",
    benefits: "100 days guaranteed wage employment/year. Current wages: ₹204-333/day depending on state. Work must be provided within 15 days of demand.",
    how_to_apply: "1. Visit Gram Panchayat office\n2. Apply for Job Card with photo, Aadhaar\n3. Job Card issued within 15 days\n4. Demand work in writing at GP\n5. Work provided within 15 days or unemployment allowance paid",
    documents: "Aadhaar card, 2 passport photos, Bank/post office account details",
    helpline: "MGNREGA helpline: 1800-345-22-44"
  }
};

// ===== State =====
let chatHistory = [];
let uploadedPDF = null;
let currentCategory = 'all';

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
  renderPolicies();
  initHeroAnimation();
  loadHistory();
});

function initHeroAnimation() {
  setTimeout(() => {
    document.getElementById('typingDots').style.display = 'none';
    const ans = document.getElementById('previewAnswer');
    ans.style.display = 'block';
    ans.style.animation = 'fadeUp 0.5s ease';
  }, 2200);
}

// ===== Rendering =====
function renderPolicies(filter = '', category = 'all') {
  const grid = document.getElementById('policyGrid');
  const filtered = POLICIES_DB.filter(p => {
    const matchCat = category === 'all' || p.category === category;
    const matchText = !filter || p.name.toLowerCase().includes(filter.toLowerCase()) || p.desc.toLowerCase().includes(filter.toLowerCase());
    return matchCat && matchText;
  });

  grid.innerHTML = filtered.map(p => `
    <div class="policy-card" onclick="askAbout('${p.name}')">
      <div class="policy-card-header">
        <div class="policy-icon">${p.icon}</div>
        <div>
          <div class="policy-name">${p.name}</div>
          <div class="policy-ministry">${p.ministry}</div>
        </div>
      </div>
      <div class="policy-desc">${p.desc}</div>
      <div class="policy-tags">
        ${p.tags.map(t => `<span class="ptag ${p.benefit ? 'benefit' : ''}">${t}</span>`).join('')}
      </div>
    </div>
  `).join('');

  if (!filtered.length) grid.innerHTML = `<p style="color:var(--text-muted); grid-column:1/-1; text-align:center; padding:2rem;">No schemes found.</p>`;
}

function filterPolicies(val) { renderPolicies(val, currentCategory); }

function filterByCategory(cat, btn) {
  currentCategory = cat;
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  renderPolicies(document.querySelector('.policy-search-bar input').value, cat);
}

// ===== Chat =====
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function sendSuggestion(btn) {
  document.getElementById('chatInput').value = btn.textContent;
  sendMessage();
}

function askAbout(schemeName) {
  document.getElementById('chat').scrollIntoView({ behavior: 'smooth' });
  setTimeout(() => {
    document.getElementById('chatInput').value = `Tell me about ${schemeName} — eligibility, benefits, and how to apply`;
    sendMessage();
  }, 400);
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) return;

  const lang = document.getElementById('langSelect').value;

  // Clear welcome card
  const welcome = document.querySelector('.welcome-card');
  if (welcome) welcome.remove();

  // Add user message
  addMessage('user', msg);
  chatHistory.push({ role: 'user', content: msg });
  addToHistory(msg);
  input.value = '';
  input.style.height = 'auto';

  // Thinking indicator
  const thinkId = addThinking();

  // Disable send
  const sendBtn = document.getElementById('sendBtn');
  sendBtn.disabled = true;

  try {
    const response = await callClaudeAPI(msg, lang);
    removeThinking(thinkId);
    addMessage('bot', response);
    chatHistory.push({ role: 'assistant', content: response });
  } catch (err) {
    removeThinking(thinkId);
    addMessage('bot', `⚠️ Unable to connect to AI service. Please check your API key configuration in config/settings.json.\n\nError: ${err.message}`);
  }

  sendBtn.disabled = false;
  scrollToBottom();
}

async function callClaudeAPI(userMessage, lang = 'en') {
  // Calls our FastAPI backend /api/chat — API key is secure on server side
  // Backend runs FAISS retrieval + Claude RAG pipeline
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: userMessage,
      language: lang,
      history: chatHistory.slice(-10)
    })
  });

  if (!response.ok) {
    let errMsg = 'Server error ' + response.status;
    try { const err = await response.json(); errMsg = err.detail || errMsg; } catch (_) {}
    throw new Error(errMsg);
  }

  const data = await response.json();
  return data.answer || 'No response received.';
}

function buildRAGContext(query) {
  // Simple keyword-based local retrieval (in production, this would use FAISS/vector embeddings)
  const q = query.toLowerCase();
  let context = '';

  for (const [scheme, info] of Object.entries(SCHEME_KNOWLEDGE)) {
    if (q.includes(scheme.toLowerCase()) || q.includes(scheme.toLowerCase().split(' ').pop())) {
      context += `\n=== ${scheme} ===\n`;
      context += `Eligibility: ${info.eligibility}\n`;
      context += `Benefits: ${info.benefits}\n`;
      context += `How to Apply: ${info.how_to_apply}\n`;
      context += `Documents: ${info.documents}\n`;
      context += `Helpline: ${info.helpline}\n`;
    }
  }

  if (!context) {
    // General Indian policy context
    context = `General Schemes Available: ${POLICIES_DB.map(p => p.name).join(', ')}\n`;
    context += `Common eligibility: Aadhaar, BPL/income criteria, bank account\n`;
    context += `Common portals: pmkisan.gov.in, pmjay.gov.in, pmaymis.gov.in, nrega.nic.in\n`;
    context += `Universal helpline: 1800-11-0001 (India govt services)\n`;
  }

  return context;
}

// ===== DOM Helpers =====
function addMessage(role, text) {
  const msgs = document.getElementById('chatMessages');
  const isUser = role === 'user';
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const html = `
    <div class="msg-row ${role}">
      <div class="msg-avatar">${isUser ? '👤' : '⚖'}</div>
      <div>
        <div class="msg-bubble">${formatMessage(text)}</div>
        <div class="msg-meta">${time}</div>
      </div>
    </div>
  `;

  msgs.insertAdjacentHTML('beforeend', html);
  scrollToBottom();
}

function formatMessage(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, `<code style="background:rgba(232,160,69,0.1);padding:0.1rem 0.3rem;border-radius:3px;font-family:var(--font-mono);font-size:0.8em;">$1</code>`)
    .replace(/\n/g, '<br/>')
    .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" style="color:var(--accent)">$1</a>');
}

function addThinking() {
  const id = 'think-' + Date.now();
  const msgs = document.getElementById('chatMessages');
  msgs.insertAdjacentHTML('beforeend', `
    <div class="msg-row bot" id="${id}">
      <div class="msg-avatar">⚖</div>
      <div class="thinking-bubble">
        <span></span><span></span><span></span>
      </div>
    </div>
  `);
  scrollToBottom();
  return id;
}

function removeThinking(id) {
  document.getElementById(id)?.remove();
}

function scrollToBottom() {
  const msgs = document.getElementById('chatMessages');
  msgs.scrollTop = msgs.scrollHeight;
}

function clearChat() {
  const msgs = document.getElementById('chatMessages');
  msgs.innerHTML = `
    <div class="welcome-card">
      <div class="welcome-icon">🏛</div>
      <h3>Chat Cleared</h3>
      <p>Ask me anything about government schemes!</p>
    </div>
  `;
  chatHistory = [];
}

// ===== PDF Upload =====
function handlePDF(input) {
  const file = input.files[0];
  if (!file) return;
  uploadedPDF = file;
  document.getElementById('pdfTag').style.display = 'inline-flex';
  document.getElementById('pdfName').textContent = file.name;
  addMessage('bot', `📄 PDF uploaded: **${file.name}**\n\nI'll use this document to answer your questions. What would you like to know about it?`);
}

function removePDF() {
  uploadedPDF = null;
  document.getElementById('pdfTag').style.display = 'none';
  document.getElementById('pdfInput').value = '';
}

// ===== History =====
function addToHistory(msg) {
  const list = document.getElementById('historyList');
  const empty = list.querySelector('.empty-history');
  if (empty) empty.remove();
  const item = document.createElement('div');
  item.className = 'history-item';
  item.textContent = msg;
  item.onclick = () => {
    document.getElementById('chatInput').value = msg;
  };
  list.insertBefore(item, list.firstChild);
  // Keep only last 8
  while (list.children.length > 8) list.removeChild(list.lastChild);
}

function loadHistory() { /* Extend with localStorage if needed */ }
