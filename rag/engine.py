"""
NyayaBot RAG Engine - Production Version
Uses TF-IDF + Groq Llama 3.3 - No torch/sentence-transformers needed
"""

import os, json, time, logging, re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

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


@dataclass
class PolicyChunk:
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
    chunk: PolicyChunk
    score: float
    rank: int


@dataclass
class ChatResponse:
    answer: str
    language: str
    sources: List[str]
    scheme_names: List[str]
    retrieval_time_ms: float
    llm_time_ms: float
    total_time_ms: float
    confidence: float


class PolicyDocumentProcessor:
    def __init__(self, chunk_size=512, overlap=64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process_pdf(self, pdf_path: str, scheme_name: str) -> List[PolicyChunk]:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            full_text = ""
            for page in doc:
                full_text += page.get_text("text") + "\n\n"
            doc.close()
            return self.process_text(full_text, scheme_name, Path(pdf_path).name)
        except Exception as e:
            logger.error(f"PDF error: {e}")
            return []

    def process_text(self, text: str, scheme_name: str, source: str = "manual") -> List[PolicyChunk]:
        chunks = []
        words = text.split()
        chunk_idx = 0
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            if len(chunk_text.strip()) < 20:
                continue
            chunk = PolicyChunk(
                chunk_id=f"{scheme_name}_{chunk_idx:04d}",
                scheme_name=scheme_name,
                section="General",
                content=chunk_text,
                source_file=source,
                page_num=1
            )
            chunks.append(chunk)
            chunk_idx += 1
        return chunks


class TFIDFVectorStore:
    """Simple TF-IDF based vector store - no FAISS needed"""

    def __init__(self, **kwargs):
        self.chunks: List[PolicyChunk] = []
        self.vectorizer = None
        self.matrix = None
        logger.info("Using TF-IDF vector store (no FAISS)")

    def add_chunks(self, chunks: List[PolicyChunk], embedder=None):
        self.chunks.extend(chunks)
        self._rebuild_index()
        logger.info(f"Vector store: {len(self.chunks)} chunks")

    def _rebuild_index(self):
        if not self.chunks:
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words=None
            )
            texts = [c.content for c in self.chunks]
            self.matrix = self.vectorizer.fit_transform(texts)
            logger.info(f"TF-IDF index built: {self.matrix.shape}")
        except Exception as e:
            logger.error(f"Index build error: {e}")

    def search(self, query_embedding, top_k: int = 5) -> List[RetrievalResult]:
        return []

    def search_text(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        if not self.chunks or self.vectorizer is None or self.matrix is None:
            return []
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            q_vec = self.vectorizer.transform([query])
            scores = cosine_similarity(q_vec, self.matrix).flatten()
            top_indices = np.argsort(scores)[::-1][:top_k]
            results = []
            for rank, idx in enumerate(top_indices):
                if scores[idx] > 0:
                    results.append(RetrievalResult(
                        chunk=self.chunks[idx],
                        score=float(scores[idx]),
                        rank=rank + 1
                    ))
            return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def save(self):
        pass  # No persistence needed for TF-IDF

    def load(self):
        return False  # Always rebuild


class EmbeddingEngine:
    """Dummy embedding engine - TF-IDF handles everything"""
    def __init__(self, **kwargs):
        self.dimension = 100
        self.model = None
        self.model_name = "tfidf"
        logger.info("Using TF-IDF embeddings (lightweight deployment mode)")

    def embed(self, texts):
        return np.zeros((len(texts), self.dimension))

    def embed_single(self, text):
        return np.zeros(self.dimension)


class TranslationEngine:
    SUPPORTED_LANGS = {
        "en": "English", "hi": "Hindi", "ta": "Tamil", "bn": "Bengali",
        "te": "Telugu", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada",
        "ml": "Malayalam", "pa": "Punjabi", "ur": "Urdu", "or": "Odia"
    }

    def __init__(self):
        self.backend = None
        try:
            from deep_translator import GoogleTranslator
            self.backend = "deep_translator"
            logger.info("Translation: using deep-translator backend")
        except ImportError:
            logger.warning("Translation disabled")

    def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        if target_lang == source_lang or target_lang == "en":
            return text
        if not self.backend:
            return text
        try:
            from deep_translator import GoogleTranslator
            return GoogleTranslator(source=source_lang, target=target_lang).translate(text) or text
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    def detect_language(self, text: str) -> str:
        if any("\u0900" <= c <= "\u097F" for c in text):
            return "hi"
        if any("\u0B80" <= c <= "\u0BFF" for c in text):
            return "ta"
        if any("\u0980" <= c <= "\u09FF" for c in text):
            return "bn"
        if any("\u0C00" <= c <= "\u0C7F" for c in text):
            return "te"
        return "en"


class NyayaBotRAGEngine:
    SYSTEM_PROMPT = """You are NyayaBot, an expert AI assistant helping Indian citizens understand government welfare schemes and policies.

Your role:
- Explain policies in SIMPLE, PLAIN language
- Structure: What is it -> Who is eligible -> Benefits -> How to apply -> Documents -> Helpline
- Be accurate, helpful, and empathetic
- Always include amounts, deadlines, helpline numbers

Retrieved Policy Context:
{context}

Answer in: {language}"""

    def __init__(self, api_key=None, vector_store_path="data/faiss_index", policies_dir="data/policies"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
        self.policies_dir = Path(policies_dir)

        self.processor = PolicyDocumentProcessor()
        self.embedder = EmbeddingEngine()
        self.vector_store = TFIDFVectorStore()
        self.translator = TranslationEngine()

        self.provider = self._detect_provider()
        self.client = self._init_client()

        logger.info("Building knowledge base from training data...")
        self._load_builtin_knowledge()
        self.ingest_all_policies()

    def _detect_provider(self):
        groq_key = os.getenv("GROQ_API_KEY", "")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if groq_key and "your_" not in groq_key:
            logger.info("AI Provider: Groq (free)")
            return "groq"
        elif anthropic_key and "your_" not in anthropic_key:
            logger.info("AI Provider: Anthropic")
            return "anthropic"
        logger.warning("No AI API key found! Set GROQ_API_KEY in .env")
        return "none"

    def _init_client(self):
        if self.provider == "groq" and GROQ_AVAILABLE:
            return Groq(api_key=os.getenv("GROQ_API_KEY"))
        elif self.provider == "anthropic" and ANTHROPIC_AVAILABLE:
            return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return None

    def ingest_all_policies(self):
        self.policies_dir.mkdir(parents=True, exist_ok=True)
        chunks = []
        for pdf in self.policies_dir.glob("*.pdf"):
            scheme = pdf.stem.replace("_", " ").title()
            chunks.extend(self.processor.process_pdf(str(pdf), scheme))
        for txt in self.policies_dir.glob("*.txt"):
            scheme = txt.stem.replace("_", " ").title()
            text = txt.read_text(encoding="utf-8", errors="ignore")
            chunks.extend(self.processor.process_text(text, scheme, txt.name))
        if chunks:
            self.vector_store.add_chunks(chunks)

    def _load_builtin_knowledge(self):
        training_file = Path("data/training/training_data.json")
        if not training_file.exists():
            training_file = Path(__file__).parent.parent / "data" / "training" / "training_data.json"
        if not training_file.exists():
            logger.warning("No training data found")
            return
        try:
            with open(training_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            chunks = []
            for doc in data.get("policy_documents", []):
                text = f"{doc['title']}\n\n{doc['content']}"
                chunks.extend(self.processor.process_text(text, doc["title"], "training_data.json"))
            if chunks:
                self.vector_store.add_chunks(chunks)
                logger.info(f"Loaded {len(chunks)} chunks from training data")
        except Exception as e:
            logger.error(f"Training data error: {e}")

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        start = time.time()
        results = self.vector_store.search_text(query, top_k=top_k)
        elapsed = (time.time() - start) * 1000
        logger.debug(f"Retrieval: {len(results)} chunks in {elapsed:.0f}ms")
        return results

    def chat(self, user_message: str, language: str = "en", conversation_history=None, top_k: int = 5) -> ChatResponse:
        t_start = time.time()

        if language == "auto":
            language = self.translator.detect_language(user_message)

        query_en = user_message
        if language != "en":
            query_en = self.translator.translate(user_message, "en", language)

        t_retrieve = time.time()
        results = self.retrieve(query_en, top_k=top_k)
        retrieval_ms = (time.time() - t_retrieve) * 1000

        context = self._build_context(results)
        sources = list(set(r.chunk.source_file for r in results))
        scheme_names = list(set(r.chunk.scheme_name for r in results))

        lang_name = self.translator.SUPPORTED_LANGS.get(language, "English")
        system = self.SYSTEM_PROMPT.format(context=context, language=lang_name)

        messages = []
        if conversation_history:
            for turn in conversation_history[-8:]:
                messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_message})

        t_llm = time.time()
        answer = self._call_llm(system, messages)
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
            confidence=max((r.score for r in results), default=0.0)
        )

    def _build_context(self, results: List[RetrievalResult]) -> str:
        if not results:
            return "No specific policy documents found. Answer based on general knowledge of Indian government schemes."
        parts = []
        for r in results:
            c = r.chunk
            parts.append(f"[Source: {c.scheme_name} | Score: {r.score:.2f}]\n{c.content}")
        return "\n\n---\n\n".join(parts)

    def _call_llm(self, system: str, messages: List[Dict]) -> str:
        if not self.client or self.provider == "none":
            return ("No AI API key configured! Add GROQ_API_KEY to Railway Variables.\n"
                    "Get free key at: console.groq.com")
        try:
            if self.provider == "groq":
                groq_messages = [{"role": "system", "content": system}] + messages
                response = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    max_tokens=1500,
                    messages=groq_messages,
                    temperature=0.3
                )
                return response.choices[0].message.content
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1500,
                    system=system,
                    messages=messages
                )
                return response.content[0].text
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"AI error: {str(e)}"

    def add_document(self, text: str, scheme_name: str, source: str = "user_upload") -> int:
        chunks = self.processor.process_text(text, scheme_name, source)
        if chunks:
            self.vector_store.add_chunks(chunks)
        return len(chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = NyayaBotRAGEngine()
    print("NyayaBot ready!")
    r = engine.chat("What is PM-KISAN?", language="en")
    print("Answer:", r.answer[:200])
