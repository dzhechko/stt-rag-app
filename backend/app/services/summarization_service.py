import logging
import httpx
from typing import Optional, Dict, Any, List
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)


class SummarizationService:
    def __init__(self):
        # Validate and clean base_url (same as TranscriptionService)
        base_url = settings.evolution_base_url
        if not base_url:
            raise ValueError("EVOLUTION_BASE_URL is not set in environment variables")
        
        # Clean up base_url if it contains the variable name prefix
        original_url = base_url
        if "EVOLUTION_BASE_URL=" in base_url:
            last_eq_index = base_url.rfind("=")
            if last_eq_index >= 0:
                base_url = base_url[last_eq_index + 1:].strip()
                logger.warning(f"Cleaned malformed base_url: '{original_url}' -> '{base_url}'")
        
        if not base_url.startswith(('http://', 'https://')):
            raise ValueError(f"EVOLUTION_BASE_URL must start with http:// or https://, got: {base_url}")
        
        logger.info(f"Initializing SummarizationService with base_url: {base_url}")
        
        # Create custom HTTP client with SSL verification disabled for internal Cloud.ru endpoints
        # Increased timeouts for translation operations which may take longer
        http_client = httpx.Client(
            verify=False,  # Disable SSL verification for internal Cloud.ru endpoints
            timeout=httpx.Timeout(300.0, connect=60.0),  # 5 minutes for translation, 1 minute for connection
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        self.client = OpenAI(
            api_key=settings.evolution_api_key,
            base_url=base_url,
            http_client=http_client,
            max_retries=2
        )
        self.default_model = "GigaChat/GigaChat-2-Max"
        self.chunk_size = 8000  # tokens (approximate)
    
    def translate_text(
        self,
        text: str,
        source_language: str = "en",
        target_language: str = "ru",
        model: Optional[str] = None
    ) -> str:
        """
        Translate text from source language to target language using GigaChat
        
        Args:
            text: Text to translate
            source_language: Source language code (default: "en")
            target_language: Target language code (default: "ru")
            model: Model to use (default: GigaChat-2-Max)
        
        Returns:
            Translated text
        """
        model = model or self.default_model
        
        # If text is too long, split into chunks and translate separately
        max_chunk_length = 3000  # Characters per chunk (approximately 750 tokens)
        if len(text) > max_chunk_length:
            logger.info(f"Text is too long ({len(text)} chars), splitting into chunks for translation")
            return self._translate_large_text(text, source_language, target_language, model)
        
        lang_names = {
            "en": "английский",
            "ru": "русский",
            "de": "немецкий",
            "fr": "французский",
            "es": "испанский"
        }
        
        source_lang_name = lang_names.get(source_language, source_language)
        target_lang_name = lang_names.get(target_language, target_language)
        
        prompt = (
            f"Переведи следующий текст с {source_lang_name} на {target_lang_name} язык. "
            f"Сохрани смысл, структуру и стиль текста. Не добавляй комментарии или пояснения, только перевод:\n\n{text}"
        )
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты профессиональный переводчик. Переводишь текст точно, сохраняя смысл и стиль оригинала."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=8000
            )
            
            translated_text = response.choices[0].message.content.strip()
            logger.info(f"Successfully translated text from {source_language} to {target_language} ({len(text)} chars)")
            return translated_text
            
        except Exception as e:
            logger.error(f"Error translating text: {str(e)}", exc_info=True)
            raise
    
    def _translate_large_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
        model: Optional[str] = None
    ) -> str:
        """
        Translate large text by splitting it into chunks
        
        Args:
            text: Long text to translate
            source_language: Source language code
            target_language: Target language code
            model: Model to use
        
        Returns:
            Translated text
        """
        model = model or self.default_model
        chunk_size = 3000  # Characters per chunk
        
        # Split text into chunks (try to split at sentence boundaries)
        chunks = []
        current_chunk = ""
        
        # Simple splitting by sentences (period, exclamation, question mark)
        sentences = text.replace('!', '.\n').replace('?', '.\n').split('.')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # If adding this sentence would exceed chunk size, save current chunk
            if len(current_chunk) + len(sentence) + 1 > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + "."
            else:
                current_chunk += (sentence + "." if not current_chunk.endswith('.') else " " + sentence + ".")
        
        # Add last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        logger.info(f"Splitting text into {len(chunks)} chunks for translation")
        
        # Translate each chunk (use direct API call to avoid recursion)
        translated_chunks = []
        lang_names = {
            "en": "английский",
            "ru": "русский",
            "de": "немецкий",
            "fr": "французский",
            "es": "испанский"
        }
        source_lang_name = lang_names.get(source_language, source_language)
        target_lang_name = lang_names.get(target_language, target_language)
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Translating chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            try:
                prompt = (
                    f"Переведи следующий текст с {source_lang_name} на {target_lang_name} язык. "
                    f"Сохрани смысл, структуру и стиль текста. Не добавляй комментарии или пояснения, только перевод:\n\n{chunk}"
                )
                
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Ты профессиональный переводчик. Переводишь текст точно, сохраняя смысл и стиль оригинала."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=8000
                )
                
                translated_chunk = response.choices[0].message.content.strip()
                translated_chunks.append(translated_chunk)
            except Exception as e:
                logger.error(f"Error translating chunk {i+1}: {str(e)}")
                # If chunk translation fails, try to continue with other chunks
                translated_chunks.append(f"[Translation error for chunk {i+1}]")
        
        # Combine translated chunks
        translated_text = " ".join(translated_chunks)
        logger.info(f"Successfully translated large text ({len(text)} chars -> {len(translated_text)} chars)")
        return translated_text
    
    def summarize(
        self,
        text: str,
        template: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        fields_config: Optional[Dict[str, bool]] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Summarize transcript text
        
        Args:
            text: Transcript text to summarize
            template: Template name (meeting, interview, lecture, podcast)
            custom_prompt: Custom prompt text
            fields_config: Dictionary of fields to include (participants, decisions, deadlines, topics)
            model: Model to use (default: GigaChat-2-Max)
        
        Returns:
            Dictionary with summary text and metadata
        """
        model = model or self.default_model
        
        # Build prompt based on template or custom prompt
        if custom_prompt:
            prompt = self._build_custom_prompt(text, custom_prompt, fields_config)
        elif template:
            prompt = self._build_template_prompt(text, template, fields_config)
        else:
            prompt = self._build_default_prompt(text, fields_config)
        
        # Check if text needs chunking
        estimated_tokens = len(text) // 4  # Rough estimation
        if estimated_tokens > self.chunk_size:
            return self._summarize_large_text(text, prompt, model, fields_config)
        
        # Single request summarization
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты профессиональный помощник по анализу встреч. Создаешь четкие, структурированные резюме."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=3000
            )
            
            summary_text = response.choices[0].message.content
            
            return {
                "summary_text": summary_text,
                "model_used": model,
                "template": template,
                "fields_config": fields_config
            }
        
        except Exception as e:
            logger.error(f"Error in summarization: {str(e)}", exc_info=True)
            raise
    
    def _build_default_prompt(self, text: str, fields_config: Optional[Dict[str, bool]] = None) -> str:
        """Build default summarization prompt"""
        fields = []
        if fields_config:
            if fields_config.get("participants", True):
                fields.append("участники")
            if fields_config.get("decisions", True):
                fields.append("ключевые решения")
            if fields_config.get("deadlines", True):
                fields.append("сроки и ответственные")
            if fields_config.get("topics", True):
                fields.append("основные темы")
        
        fields_text = ", ".join(fields) if fields else "основные моменты"
        
        return f"""Проанализируй транскрипцию и создай краткое резюме (300-500 слов).
Выдели следующие аспекты:
- Основная тема
- {fields_text}

Транскрипция:
{text}"""
    
    def _build_template_prompt(self, text: str, template: str, fields_config: Optional[Dict[str, bool]] = None) -> str:
        """Build prompt based on template"""
        templates = {
            "meeting": {
                "title": "Резюме встречи",
                "fields": [
                    "**Дата/Время:** [если упоминается]",
                    "**Участники:** [список]",
                    "**Продолжительность:** [если видно из контекста]",
                    "### Основная тема",
                    "[1-2 предложения]",
                    "### Ключевые обсуждаемые вопросы",
                    "- [Пункт 1]",
                    "- [Пункт 2]",
                    "### Принятые решения",
                    "- [Решение 1]",
                    "### Ответственные и сроки",
                    "| Что | Кто | Срок |",
                    "|-----|-----|------|",
                    "### Следующие шаги",
                    "1. [Шаг 1]",
                    "### Открытые вопросы",
                    "- [Вопрос 1]"
                ]
            },
            "interview": {
                "title": "Резюме интервью",
                "fields": [
                    "### Основная тема интервью",
                    "### Ключевые моменты",
                    "- [Момент 1]",
                    "### Важные цитаты",
                    "> [Цитата]",
                    "### Выводы"
                ]
            },
            "lecture": {
                "title": "Резюме лекции",
                "fields": [
                    "### Тема лекции",
                    "### Основные концепции",
                    "- [Концепция 1]",
                    "### Ключевые примеры",
                    "### Важные выводы"
                ]
            },
            "podcast": {
                "title": "Резюме подкаста",
                "fields": [
                    "### Тема эпизода",
                    "### Основные обсуждения",
                    "- [Обсуждение 1]",
                    "### Ключевые моменты",
                    "### Рекомендации"
                ]
            }
        }
        
        template_config = templates.get(template, templates["meeting"])
        structure = "\n".join(template_config["fields"])
        
        return f"""Проанализируй транскрипцию и создай резюме в следующем формате:

## {template_config["title"]}

{structure}

---

Транскрипция:
{text}"""
    
    def _build_custom_prompt(self, text: str, custom_prompt: str, fields_config: Optional[Dict[str, bool]] = None) -> str:
        """Build prompt from custom text"""
        return f"""{custom_prompt}

Транскрипция:
{text}"""
    
    def _summarize_large_text(
        self,
        text: str,
        prompt_template: str,
        model: str,
        fields_config: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """Summarize large text by chunking"""
        # Split text into chunks (rough character-based splitting)
        chunk_size_chars = self.chunk_size * 4  # Rough conversion
        chunks = [text[i:i+chunk_size_chars] for i in range(0, len(text), chunk_size_chars)]
        
        logger.info(f"Summarizing large text in {len(chunks)} chunks")
        
        summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            
            # Build prompt for chunk
            chunk_prompt = f"Кратко резюмируй следующую часть транскрипции:\n\n{chunk}"
            
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": chunk_prompt
                        }
                    ],
                    temperature=0.2,
                    max_tokens=1000
                )
                summaries.append(response.choices[0].message.content)
            except Exception as e:
                logger.error(f"Error summarizing chunk {i+1}: {str(e)}")
                raise
        
        # Final summary of all chunks
        combined_summaries = "\n---\n".join(summaries)
        final_prompt = f"Объедини следующие резюме частей в одно финальное резюме:\n\n{combined_summaries}"
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты профессиональный помощник по анализу встреч. Создаешь четкие, структурированные резюме."
                    },
                    {
                        "role": "user",
                        "content": final_prompt
                    }
                ],
                temperature=0.2,
                max_tokens=3000
            )
            
            final_summary = response.choices[0].message.content
            
            return {
                "summary_text": final_summary,
                "model_used": model,
                "template": None,
                "fields_config": fields_config,
                "chunked": True,
                "chunks_processed": len(chunks)
            }
        
        except Exception as e:
            logger.error(f"Error creating final summary: {str(e)}", exc_info=True)
            raise

