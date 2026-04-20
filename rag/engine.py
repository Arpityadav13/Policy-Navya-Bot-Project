"""
NyayaBot RAG Engine
Policy-to-Citizen AI Chatbot Backend
Powered by Claude AI + FAISS + LlamaIndex
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np

# Support both Groq (free) and Anthropic
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


# ===== DATA MODELS =====
@dataclass
class PolicyChunk:
    """Represents a chunk of policy document"""
    chunk_id: str
    scheme_name: str
    section: str
    content: str
    source_file: str
    page_num: int
    embedding: Optional[np.ndarray] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result from vector store retrieval"""
    chunk: PolicyChunk
    score: float
    rank: int


@dataclass
class ChatResponse:
    """Full chat response with metadata"""
    answer: str
    language: str
    sources: List[str]
    scheme_names: List[str]
    retrieval_time_ms: float
    llm_time_ms: float
    total_time_ms: float
    confidence: float


# ===== DOCUMENT PROCESSOR =====
class PolicyDocumentProcessor:
    """Processes government policy PDFs into chunks"""

    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process_pdf(self, pdf_path: str, scheme_name: str) -> List[PolicyChunk]:
        """Extract and chunk text from a policy PDF"""
        try:
            import fitz  # PyMuPDF
            chunks = []
            doc = fitz.open(pdf_path)

            full_text = ""
            page_map = []  # (start_char, page_num)

            for page_num, page in enumerate(doc):
                text = page.get_text("text")
                page_map.append((len(full_text), page_num + 1))
                full_text += text + "\n\n"

            doc.close()

            # Section-aware chunking
            sections = self._detect_sections(full_text)
            chunk_idx = 0

            for section_name, section_text in sections:
                words = section_text.split()
                for i in range(0, len(words), self.chunk_size - self.overlap):
                    chunk_words = words[i:i + self.chunk_size]
                    chunk_text = " ".join(chunk_words)

                    # Find page number
                    char_pos = full_text.find(chunk_text[:50])
                    page_num = 1
                    for start_char, pnum in page_map:
                        if start_char <= char_pos:
                            page_num = pnum

                    chunk = PolicyChunk(
                        chunk_id=f"{scheme_name}_{chunk_idx:04d}",
                        scheme_name=scheme_name,
                        section=section_name,
                        content=chunk_text,
                        source_file=Path(pdf_path).name,
                        page_num=page_num
                    )
                    chunks.append(chunk)
                    chunk_idx += 1

            logger.info(f"Processed {pdf_path}: {len(chunks)} chunks")
            return chunks

        except ImportError:
            logger.warning("PyMuPDF not installed. Using fallback text processing.")
            return self._process_text_fallback(pdf_path, scheme_name)
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            return []

    def process_text(self, text: str, scheme_name: str, source: str = "manual") -> List[PolicyChunk]:
        """Process raw text into chunks"""
        sections = self._detect_sections(text)
        chunks = []
        chunk_idx = 0

        for section_name, section_text in sections:
            words = section_text.split()
            for i in range(0, len(words), self.chunk_size - self.overlap):
                chunk_words = words[i:i + self.chunk_size]
                chunk_text = " ".join(chunk_words)
                if len(chunk_text.strip()) < 20:
                    continue
                chunk = PolicyChunk(
                    chunk_id=f"{scheme_name}_{chunk_idx:04d}",
                    scheme_name=scheme_name,
                    section=section_name,
                    content=chunk_text,
                    source_file=source,
                    page_num=1
                )
                chunks.append(chunk)
                chunk_idx += 1

        return chunks

    def _detect_sections(self, text: str) -> List[Tuple[str, str]]:
        """Detect logical sections in policy text"""
        import re
        section_patterns = [
            r'^#+\s+(.+)$',           # Markdown headers
            r'^([A-Z][A-Z\s]{3,})$',  # ALL CAPS headers
            r'^\d+\.\s+([A-Z].+)$',   # Numbered sections
            r'^(?:Section|Chapter|Part)\s+\d+',  # Explicit section labels
        ]
        combined = '|'.join(section_patterns)
        parts = re.split(combined, text, flags=re.MULTILINE)

        if len(parts) <= 1:
            return [("General", text)]

        sections = []
        current_section = "Introduction"
        current_text = ""

        for part in parts:
            if part and re.match(combined, part.strip(), re.MULTILINE):
                if current_text.strip():
                    sections.append((current_section, current_text))
                current_section = part.strip()[:60]
                current_text = ""
            else:
                current_text += part

        if current_text.strip():
            sections.append((current_section, current_text))

        return sections if sections else [("General", text)]

    def _process_text_fallback(self, file_path: str, scheme_name: str) -> List[PolicyChunk]:
        """Fallback: read as plain text"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return self.process_text(text, scheme_name, Path(file_path).name)
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return []


# ===== EMBEDDING ENGINE =====
class EmbeddingEngine:
    """Generates text embeddings for semantic search"""

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model
        self.model = None
        self.dimension = 384
        self.vectorizer = None   # ✅ ADD THIS
        self._load_model()
        

    def _load_model(self):
        # Use TF-IDF only - no heavy torch/sentence-transformers needed
        self.model = None
        logger.info("Using TF-IDF embeddings (lightweight deployment mode)")

    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        if self.model:
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return embeddings
        else:
            return self._tfidf_embed(texts)

    def embed_single(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    def _tfidf_embed(self, texts: List[str]) -> np.ndarray:
        """Simple TF-IDF based embedding fallback"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(max_features=384)
        try:
            matrix = vectorizer.fit_transform(texts)
            arr = matrix.toarray()
            # Normalize
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1
            return arr / norms
        except Exception:
            return np.random.rand(len(texts), 384).astype(np.float32)


# ===== FAISS VECTOR STORE =====
class FAISSVectorStore:
    """FAISS-based vector store for policy chunks"""

    def __init__(self, dimension: int = 384, index_path: str = "data/faiss_index"):
        self.dimension = dimension
        self.index_path = Path(index_path)
        self.index = None
        self.chunks: List[PolicyChunk] = []
        self._init_index()

    def _init_index(self):
        try:
            import faiss
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine sim)
            logger.info(f"FAISS index initialized (dim={self.dimension})")
        except ImportError:
            logger.warning("FAISS not installed. Using numpy-based search.")
            self.index = None

    def add_chunks(self, chunks: List[PolicyChunk], embedder: EmbeddingEngine):
        """Add chunks with embeddings to vector store"""
        texts = [c.content for c in chunks]
        embeddings = embedder.embed(texts)

        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb.astype(np.float32)

        self.chunks.extend(chunks)

        if self.index:
            import faiss
            emb_matrix = np.array([c.embedding for c in self.chunks], dtype=np.float32)
            # Normalize for cosine similarity
            faiss.normalize_L2(emb_matrix)
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(emb_matrix)
        
        logger.info(f"Vector store: {len(self.chunks)} total chunks")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[RetrievalResult]:
        """Search for most relevant chunks"""
        if not self.chunks:
            return []

        q = query_embedding.astype(np.float32).reshape(1, -1)

        if self.index:
            import faiss
            faiss.normalize_L2(q)
            scores, indices = self.index.search(q, min(top_k, len(self.chunks)))
            results = []
            for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx >= 0 and idx < len(self.chunks):
                    results.append(RetrievalResult(
                        chunk=self.chunks[idx],
                        score=float(score),
                        rank=rank + 1
                    ))
            return results
        else:
            # Numpy fallback
            all_embs = np.array([c.embedding for c in self.chunks])
            norms = np.linalg.norm(all_embs, axis=1, keepdims=True)
            all_embs_norm = all_embs / (norms + 1e-10)
            q_norm = q / (np.linalg.norm(q) + 1e-10)
            scores = (all_embs_norm @ q_norm.T).flatten()
            top_indices = np.argsort(scores)[::-1][:top_k]
            return [
                RetrievalResult(chunk=self.chunks[i], score=float(scores[i]), rank=r+1)
                for r, i in enumerate(top_indices)
            ]

    def save(self):
        """Persist index and chunks to disk"""
        self.index_path.mkdir(parents=True, exist_ok=True)
        chunks_data = []
        for c in self.chunks:
            d = {k: v for k, v in c.__dict__.items() if k != 'embedding'}
            if c.embedding is not None:
                d['embedding'] = c.embedding.tolist()
            chunks_data.append(d)
        with open(self.index_path / "chunks.json", 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(self.chunks)} chunks to {self.index_path}")

    def load(self):
        """Load persisted index"""
        chunks_file = self.index_path / "chunks.json"
        if not chunks_file.exists():
            logger.info("No existing index found")
            return False
        with open(chunks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.chunks = []
        for d in data:
            emb = np.array(d.pop('embedding'), dtype=np.float32) if 'embedding' in d else None
            chunk = PolicyChunk(**d)
            chunk.embedding = emb
            self.chunks.append(chunk)
        logger.info(f"Loaded {len(self.chunks)} chunks from disk")
        return True


# ===== TRANSLATION ENGINE =====
class TranslationEngine:
    """Multi-language translation using Google Translate / IndicTrans2"""

    SUPPORTED_LANGS = {
        'en': 'English', 'hi': 'Hindi', 'ta': 'Tamil', 'bn': 'Bengali',
        'te': 'Telugu', 'mr': 'Marathi', 'gu': 'Gujarati', 'kn': 'Kannada',
        'ml': 'Malayalam', 'pa': 'Punjabi', 'ur': 'Urdu', 'or': 'Odia'
    }

    def __init__(self):
        self.google_translate = None
        self._translator_backend = None  # 'googletrans' or 'deep_translator'
        self._init_google()

    def _init_google(self):
        # Try deep-translator first (more reliable, no httpcore conflicts)
        try:
            from deep_translator import GoogleTranslator
            self._translator_backend = 'deep_translator'
            self.google_translate = True  # flag that translation is available
            logger.info("Translation: using deep-translator backend")
            return
        except ImportError:
            pass

        # Fallback: try googletrans (may fail on newer httpcore)
        try:
            from googletrans import Translator
            self.google_translate = Translator()
            self._translator_backend = 'googletrans'
            logger.info("Translation: using googletrans backend")
        except (ImportError, AttributeError) as e:
            logger.warning(f"Translation disabled ({e}). Install deep-translator: pip install deep-translator")

    def translate(self, text: str, target_lang: str, source_lang: str = 'en') -> str:
        """Translate text to target language"""
        if target_lang == source_lang or target_lang == 'en':
            return text
        if not self.google_translate:
            logger.warning(f"Cannot translate to {target_lang}: translator not available")
            return text
        try:
            if self._translator_backend == 'deep_translator':
                from deep_translator import GoogleTranslator
                translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
                return translated or text
            else:
                result = self.google_translate.translate(text, dest=target_lang, src=source_lang)
                return result.text
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    def detect_language(self, text: str) -> str:
        """Detect the language of input text"""
        if not self.google_translate:
            return 'en'
        try:
            if self._translator_backend == 'deep_translator':
                from deep_translator import GoogleTranslator
                # Heuristic: check for Devanagari, Tamil, Bengali script
                if any('\u0900' <= c <= '\u097F' for c in text):
                    return 'hi'
                if any('\u0B80' <= c <= '\u0BFF' for c in text):
                    return 'ta'
                if any('\u0980' <= c <= '\u09FF' for c in text):
                    return 'bn'
                if any('\u0C00' <= c <= '\u0C7F' for c in text):
                    return 'te'
                return 'en'
            else:
                detected = self.google_translate.detect(text)
                return detected.lang
        except Exception:
            return 'en'


# ===== MAIN RAG ENGINE =====
class NyayaBotRAGEngine:
    """Main RAG orchestrator for NyayaBot"""

    SYSTEM_PROMPT = """You are NyayaBot, an expert AI assistant helping Indian citizens understand government welfare schemes and policies.

Your role:
- Explain policies in SIMPLE, PLAIN language that anyone can understand
- Structure responses clearly: What -> Who is eligible -> Benefits -> How to apply -> Documents -> Helpline
- Be accurate, helpful, and empathetic
- Always include important numbers like helplines, amounts, deadlines
- Use bullets and short sentences for clarity

When answering:
1. Lead with a 1-sentence summary
2. List eligibility criteria clearly
3. Quantify benefits (amounts, duration)
4. Give step-by-step application process
5. List required documents
6. End with helpline/website

Retrieved Policy Context:
{context}

Answer in: {language}
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        vector_store_path: str = "data/faiss_index",
        policies_dir: str = "data/policies"
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
        self.provider = self._detect_provider()
        self.client = self._init_client()
        self.policies_dir = Path(policies_dir)
        
        # Initialize components
        self.processor = PolicyDocumentProcessor()
        self.embedder = EmbeddingEngine()
        self.vector_store = FAISSVectorStore(
            dimension=self.embedder.dimension,
            index_path=vector_store_path
        )
        self.translator = TranslationEngine()
        
        # Load or build index
        if not self.vector_store.load():
            logger.info("Building new vector index from policy documents...")
            self.ingest_all_policies()

    def ingest_all_policies(self):
        """Ingest all policy documents from data/policies directory"""
        self.policies_dir.mkdir(parents=True, exist_ok=True)
        total_chunks = []

        # Process PDFs
        for pdf_file in self.policies_dir.glob("*.pdf"):
            scheme_name = pdf_file.stem.replace('_', ' ').replace('-', ' ').title()
            chunks = self.processor.process_pdf(str(pdf_file), scheme_name)
            total_chunks.extend(chunks)

        # Process text files
        for txt_file in self.policies_dir.glob("*.txt"):
            scheme_name = txt_file.stem.replace('_', ' ').replace('-', ' ').title()
            with open(txt_file, 'r', encoding='utf-8') as f:
                text = f.read()
            chunks = self.processor.process_text(text, scheme_name, txt_file.name)
            total_chunks.extend(chunks)

        if total_chunks:
            self.vector_store.add_chunks(total_chunks, self.embedder)
            self.vector_store.save()
            logger.info(f"Ingested {len(total_chunks)} chunks from {self.policies_dir}")
        else:
            logger.warning("No policy documents found. Loading built-in knowledge base.")
            self._load_builtin_knowledge()

    def _load_builtin_knowledge(self):
        """Load built-in training data as fallback"""
        training_file = Path("data/training/training_data.json")
        if not training_file.exists():
            logger.warning("No training data found")
            return

        with open(training_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        all_chunks = []
        for entry in data.get('policy_documents', []):
            text = f"{entry['title']}\n\n{entry['content']}"
            chunks = self.processor.process_text(text, entry['title'], "training_data.json")
            all_chunks.extend(chunks)

        if all_chunks:
            self.vector_store.add_chunks(all_chunks, self.embedder)
            self.vector_store.save()

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """Retrieve relevant policy chunks for a query"""
        start = time.time()
        query_emb = self.embedder.embed_single(query)
        results = self.vector_store.search(query_emb, top_k=top_k)
        elapsed = (time.time() - start) * 1000
        logger.debug(f"Retrieval: {len(results)} chunks in {elapsed:.0f}ms")
        return results

    def chat(
        self,
        user_message: str,
        language: str = 'en',
        conversation_history: Optional[List[Dict]] = None,
        top_k: int = 5
    ) -> ChatResponse:
        """Main chat method: retrieve + generate"""
        t_start = time.time()

        # Detect language if auto
        if language == 'auto':
            language = self.translator.detect_language(user_message)

        # Translate query to English for retrieval
        query_en = user_message
        if language != 'en':
            query_en = self.translator.translate(user_message, 'en', language)

        # Retrieve relevant chunks
        t_retrieve = time.time()
        results = self.retrieve(query_en, top_k=top_k)
        retrieval_ms = (time.time() - t_retrieve) * 1000

        # Build context
        context = self._build_context(results)
        sources = list(set(r.chunk.source_file for r in results))
        scheme_names = list(set(r.chunk.scheme_name for r in results))

        # Build messages for Claude
        lang_name = self.translator.SUPPORTED_LANGS.get(language, 'English')
        system = self.SYSTEM_PROMPT.format(context=context, language=lang_name)
        messages = []

        if conversation_history:
            for turn in conversation_history[-8:]:  # Keep last 4 turns
                messages.append({"role": turn["role"], "content": turn["content"]})

        messages.append({"role": "user", "content": user_message})

        # Call Claude
        t_llm = time.time()
        answer = self._call_claude(system, messages)
        llm_ms = (time.time() - t_llm) * 1000

        total_ms = (time.time() - t_start) * 1000

        return ChatResponse(
            answer=answer,
            language=language,
            sources=sources,
            scheme_names=scheme_names,
            retrieval_time_ms=round(retrieval_ms, 1),
            llm_time_ms=round(llm_ms, 1),
            total_time_ms=round(total_ms, 1),
            confidence=max(r.score for r in results) if results else 0.0
        )

    def _build_context(self, results: List[RetrievalResult]) -> str:
        """Build context string from retrieval results"""
        if not results:
            return "No specific policy documents found. Answer based on general knowledge of Indian government schemes."

        context_parts = []
        for r in results:
            c = r.chunk
            context_parts.append(
                f"[Source: {c.scheme_name} | Section: {c.section} | Score: {r.score:.2f}]\n{c.content}"
            )
        return "\n\n---\n\n".join(context_parts)

    def _detect_provider(self) -> str:
        """Auto-detect which AI provider to use based on available keys"""
        groq_key = os.getenv("GROQ_API_KEY", "")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

        if groq_key and groq_key != "your_groq_api_key_here":
            logger.info("AI Provider: Groq (free)")
            return "groq"
        elif anthropic_key and anthropic_key != "your_anthropic_api_key_here":
            logger.info("AI Provider: Anthropic Claude")
            return "anthropic"
        else:
            logger.warning("No AI API key found! Set GROQ_API_KEY in .env")
            return "none"

    def _init_client(self):
        """Initialize the AI client based on provider"""
        if self.provider == "groq":
            if GROQ_AVAILABLE:
                return Groq(api_key=os.getenv("GROQ_API_KEY"))
            else:
                logger.error("Groq not installed. Run: pip install groq")
                return None
        elif self.provider == "anthropic":
            if ANTHROPIC_AVAILABLE:
                return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            else:
                logger.error("Anthropic not installed. Run: pip install anthropic")
                return None
        return None

    def _call_claude(self, system: str, messages: List[Dict]) -> str:
        """Call AI API (Groq or Anthropic) and return response"""
        if not self.client or self.provider == "none":
            return (
                "WARNING No AI API key configured!\n\n"
                "Get a FREE Groq API key:\n"
                "1. Go to console.groq.com\n"
                "2. Sign up free\n"
                "3. Create API key (starts with gsk_...)\n"
                "4. Add to .env file: GROQ_API_KEY=gsk_your_key_here\n"
                "5. Restart the server"
            )

        try:
            if self.provider == "groq":
                # Groq uses OpenAI-compatible format
                # Combine system + messages for Groq
                groq_messages = [{"role": "system", "content": system}] + messages
                response = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",  # Free, fast, smart
                    max_tokens=1500,
                    messages=groq_messages,
                    temperature=0.3
                )
                return response.choices[0].message.content

            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    system=system,
                    messages=messages
                )
                return response.content[0].text

        except Exception as e:
            logger.error(f"AI API error ({self.provider}): {e}")
            err = str(e).lower()
            if "auth" in err or "key" in err or "invalid" in err:
                return f"ERROR Invalid API key for {self.provider}. Check your .env file."
            elif "rate" in err or "limit" in err:
                return "WARNING Rate limit reached. Wait a moment and try again."
            elif "model" in err:
                return f"WARNING Model not available: {str(e)}"
            return f"WARNING AI error: {str(e)}"

    def add_document(self, text: str, scheme_name: str, source: str = "user_upload") -> int:
        """Dynamically add a new policy document"""
        chunks = self.processor.process_text(text, scheme_name, source)
        if chunks:
            self.vector_store.add_chunks(chunks, self.embedder)
            self.vector_store.save()
        return len(chunks)


# ===== MAIN =====
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = NyayaBotRAGEngine()
    print("NyayaBot RAG Engine ready!")

    # Test query
    response = engine.chat(
        "What is PM-KISAN and who is eligible?",
        language="en"
    )
    print(f"\nAnswer: {response.answer[:200]}...")
    print(f"Sources: {response.sources}")
    print(f"Time: {response.total_time_ms:.0f}ms")
