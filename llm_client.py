
from dataclasses import dataclass, field

import random
from enum import Enum
import threading
from typing import List, Dict, Optional, Any
import time
from cachetools import TTLCache, LRUCache
import json
import hashlib
from collections import deque
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)






# الإعداد الصح اللي فيه الـ name
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', # رجعنا الـ name هنا
    filename='production_logs.log',
    filemode='a'
)

# هنا الـ name بياخد قيمة __name__ اللي هي اسم الملف الحالي
logger = logging.getLogger(__name__)












# ============================================================
# API KEY SETUP WITH FALLBACKS
# ============================================================
import os
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env إلى os.environ
load_dotenv()

configured_providers = {}

# 1️⃣ Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY: # سيعتبر False إذا كان المتغير غير موجود أو فارغ
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        # تجربة اتصال سريعة
        groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        configured_providers['groq'] = {
            'client': groq_client,
            'api_key': GROQ_API_KEY
        }
        print("✅ Groq configured from .env!")
    except Exception as e:
        print(f"❌ Groq failed: {e}")
else:
    print("⏭️ Groq skipped (No key in .env)")

# 2️⃣ Google AI Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        model.generate_content("Hi", generation_config={'max_output_tokens': 5})
        
        configured_providers['google'] = {
            'api_key': GOOGLE_API_KEY
        }
        print("✅ Google AI configured from .env!")
    except Exception as e:
        print(f"❌ Google AI failed: {e}")
else:
    print("⏭️ Google AI skipped (No key in .env)")

# 3️⃣ OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        configured_providers['openai'] = {
            'client': openai_client,
            'api_key': OPENAI_API_KEY
        }
        print("✅ OpenAI configured from .env!")
    except Exception as e:
        print(f"❌ OpenAI failed: {e}")
else:
    print("⏭️ OpenAI skipped (No key in .env)")

if configured_providers:
    print("\n✅ CONFIGURED PROVIDERS:")
    for provider in configured_providers:

        print(f"   • {provider.upper()}")
    USE_MOCK_MODE = False
else:
    print("\n⚠️ NO PROVIDERS CONFIGURED")
    print("🎭 ENABLING MOCK MODE for learning")
    USE_MOCK_MODE = True














# ============================================================
# CUSTOM EXCEPTION CLASSES
# ============================================================

class LLMError(Exception):
    """Base exception for LLM errors."""
    def __init__(self, message: str, provider: str = None, status_code: int = None):
        self.message = message
        self.provider = provider
        self.status_code = status_code
        super().__init__(self.message)

class RateLimitError(LLMError):
    """Rate limit exceeded - retryable."""
    def __init__(self, message: str, retry_after: float = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

class ServerError(LLMError):
    """Server-side error (5xx) - retryable."""
    pass

class TimeoutError(LLMError):
    """Request timeout - retryable."""
    pass

class ConnectionError(LLMError):
    """Network connection error - retryable."""
    pass

class AuthenticationError(LLMError):
    """Authentication failed - NOT retryable."""
    pass

class InvalidRequestError(LLMError):
    """Invalid request - NOT retryable."""
    pass

class ContentPolicyError(LLMError):
    """Content policy violation - NOT retryable."""
    pass

class QuotaExceededError(LLMError):
    """Quota/billing issue - NOT retryable."""
    pass

class ProviderUnavailableError(LLMError):
    """Provider is completely unavailable."""
    pass

class CircuitBreakerOpenError(LLMError):
    """Circuit breaker is open, not allowing requests."""
    pass

# Retryable exceptions tuple
RETRYABLE_EXCEPTIONS = (
    RateLimitError,
    ServerError,
    TimeoutError,
    ConnectionError,
)

NON_RETRYABLE_EXCEPTIONS = (
    AuthenticationError,
    InvalidRequestError,
    ContentPolicyError,
    QuotaExceededError,
)








# ============================================================
# RETRY LOGIC WITH TENACITY
# ============================================================

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 5
    min_wait: float = 1.0
    max_wait: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

class RetryHandler:
    """
    Handles retry logic with exponential backoff and jitter.
    Uses tenacity library for robust retries.
    """

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.retry_stats = {
            'total_attempts': 0,
            'successful_retries': 0,
            'failed_retries': 0
        }

    def create_retry_decorator(self):
        """
        Create a tenacity retry decorator with our configuration.
        """
        if self.config.jitter:
            wait_strategy = wait_random_exponential(
                min=self.config.min_wait,
                max=self.config.max_wait
            )
        else:
            wait_strategy = wait_exponential(
                multiplier=self.config.min_wait,
                max=self.config.max_wait
            )

        return retry(
            stop=stop_after_attempt(self.config.max_attempts),
            wait=wait_strategy,
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            before_sleep=self._log_retry_attempt,
            reraise=True
        )

    def _log_retry_attempt(self, retry_state):
        """Log retry attempts."""
        self.retry_stats['total_attempts'] += 1
        exception = retry_state.outcome.exception()
        wait_time = retry_state.next_action.sleep if retry_state.next_action else 0

        logger.warning(
            f"Retry attempt {retry_state.attempt_number}/{self.config.max_attempts} "
            f"after {type(exception).__name__}: {exception}. "
            f"Waiting {wait_time:.2f}s before next attempt."
        )

    def calculate_backoff(self, attempt: int, base_delay: float = None) -> float:
        """
        Calculate backoff time for a given attempt.
        Manual calculation for demonstration.
        """
        base = base_delay or self.config.min_wait
        exponential_delay = base * (self.config.exponential_base ** attempt)
        capped_delay = min(exponential_delay, self.config.max_wait)

        if self.config.jitter:
            # Full jitter strategy
            return random.uniform(0, capped_delay)
        return capped_delay



















# ============================================================
# CIRCUIT BREAKER IMPLEMENTATION
# ============================================================

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5       # Failures before opening
    success_threshold: int = 2       # Successes to close from half-open
    timeout: float = 60.0            # Seconds before trying half-open
    half_open_max_calls: int = 3     # Max calls in half-open state

class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.
    Prevents cascading failures and allows services to recover.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self._lock = threading.Lock()

        # Statistics
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'rejected_calls': 0,
            'state_changes': []
        }

    def _change_state(self, new_state: CircuitState):
        """Change circuit state and log."""
        old_state = self.state
        self.state = new_state
        self.stats['state_changes'].append({
            'timestamp': time.time(),
            'from': old_state.value,
            'to': new_state.value
        })
        logger.info(f"Circuit '{self.name}' state changed: {old_state.value} → {new_state.value}")

    def can_execute(self) -> bool:
        """
        Check if a request can be executed.
        Returns True if allowed, raises CircuitBreakerOpenError if not.
        """
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            elif self.state == CircuitState.OPEN:
                # Check if timeout has passed
                if self.last_failure_time:
                    elapsed = time.time() - self.last_failure_time
                    if elapsed >= self.config.timeout:
                        self._change_state(CircuitState.HALF_OPEN)
                        self.half_open_calls = 0
                        self.success_count = 0
                        return True

                self.stats['rejected_calls'] += 1
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' is OPEN. Rejecting request.",
                    provider=self.name
                )

            elif self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < self.config.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                else:
                    self.stats['rejected_calls'] += 1
                    raise CircuitBreakerOpenError(
                        f"Circuit '{self.name}' is HALF-OPEN and at max test calls.",
                        provider=self.name
                    )

        return False

    def record_success(self):
        """Record a successful call."""
        with self._lock:
            self.stats['total_calls'] += 1
            self.stats['successful_calls'] += 1

            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self._change_state(CircuitState.CLOSED)
                    self.failure_count = 0
                    self.success_count = 0

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed call."""
        with self._lock:
            self.stats['total_calls'] += 1
            self.stats['failed_calls'] += 1
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self._change_state(CircuitState.OPEN)

            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open goes back to open
                self._change_state(CircuitState.OPEN)

    def get_status(self) -> Dict:
        """Get current circuit breaker status."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'stats': self.stats
        }

















# ============================================================
# RESPONSE CACHING IMPLEMENTATION
# ============================================================

@dataclass
class CacheConfig:
    """Configuration for response caching."""
    enabled: bool = True
    ttl: int = 3600              # Time to live in seconds
    max_size: int = 1000         # Maximum cache entries
    cache_temperature_0_only: bool = True  # Only cache deterministic

class ResponseCache:
    """
    In-memory cache for LLM responses.
    Uses LRU eviction with TTL.
    """

    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.cache = TTLCache(
            maxsize=self.config.max_size,
            ttl=self.config.ttl
        )
        self._lock = threading.Lock()

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'skipped': 0,
            'evictions': 0
        }

    def _generate_key(self, model: str, messages: List[Dict],
                      temperature: float, max_tokens: int) -> str:
        """
        Generate a cache key from request parameters.
        """
        # Create a normalized representation
        normalized = json.dumps({
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens
        }, sort_keys=True)

        # Generate hash
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def get(self, model: str, messages: List[Dict],
            temperature: float, max_tokens: int) -> Optional[Dict]:
        """
        Get cached response if available.
        """
        if not self.config.enabled:
            return None

        if self.config.cache_temperature_0_only and temperature > 0:
            self.stats['skipped'] += 1
            return None

        key = self._generate_key(model, messages, temperature, max_tokens)

        with self._lock:
            if key in self.cache:
                self.stats['hits'] += 1
                cached = self.cache[key]
                cached['from_cache'] = True
                logger.debug(f"Cache HIT for key {key[:8]}...")
                return cached

            self.stats['misses'] += 1
            logger.debug(f"Cache MISS for key {key[:8]}...")
            return None

    def set(self, model: str, messages: List[Dict],
            temperature: float, max_tokens: int, response: Dict):
        """
        Store response in cache.
        """
        if not self.config.enabled:
            return

        if self.config.cache_temperature_0_only and temperature > 0:
            return

        key = self._generate_key(model, messages, temperature, max_tokens)

        with self._lock:
            self.cache[key] = response.copy()
            logger.debug(f"Cached response for key {key[:8]}...")

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.stats['hits'] + self.stats['misses']
        if total == 0:
            return 0.0
        return self.stats['hits'] / total

    def clear(self):
        """Clear the cache."""
        with self._lock:
            self.cache.clear()

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            **self.stats,
            'size': len(self.cache),
            'max_size': self.config.max_size,
            'hit_rate': f"{self.get_hit_rate():.1%}"
        }

















# ============================================================
# PRODUCTION LLM CLIENT
# ============================================================

@dataclass
class ProviderConfig:
    """Configuration for a single provider."""
    name: str
    api_key: str
    base_url: Optional[str] = None
    default_model: str = ""
    timeout: float = 60.0
    max_retries: int = 3
    priority: int = 1  # Lower = higher priority

@dataclass
class ProductionClientConfig:
    """Configuration for production client."""
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    cache_config: CacheConfig = field(default_factory=CacheConfig)
    circuit_breaker_config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    enable_fallback: bool = True
    enable_circuit_breaker: bool = True
    default_timeout: float = 60.0

class ProductionLLMClient:
    """
    Production-ready LLM client with:
    - Multi-provider support with failover
    - Retry logic with exponential backoff
    - Circuit breaker pattern
    - Response caching
    - Streaming support
    - Comprehensive monitoring
    """

    MOCK_RESPONSES = {
        "default": "This is a mock response demonstrating production patterns.",
        "error": "An error occurred (mock)."
    }

    def __init__(self, config: ProductionClientConfig = None):
        self.config = config or ProductionClientConfig()

        # Initialize components
        self.retry_handler = RetryHandler(self.config.retry_config)
        self.cache = ResponseCache(self.config.cache_config)
        # self.streaming_handler = StreamingHandler()

        # Provider management
        self.providers: Dict[str, ProviderConfig] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.provider_clients: Dict[str, Any] = {}

        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cached_responses': 0,
            'fallback_used': 0,
            'total_latency_ms': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'requests_by_provider': {}
        }

        # Request history for monitoring
        self.request_history = deque(maxlen=1000)

        # Setup mock mode
        self.mock_mode = False

    def add_provider(
        self,
        name: str,
        api_key: str,
        default_model: str,
        priority: int = 1,
        **kwargs
    ):
        """Add a provider to the client."""
        provider_config = ProviderConfig(
            name=name,
            api_key=api_key,
            default_model=default_model,
            priority=priority,
            **kwargs
        )
        self.providers[name] = provider_config

        # Initialize circuit breaker for provider
        if self.config.enable_circuit_breaker:
            self.circuit_breakers[name] = CircuitBreaker(
                name, self.config.circuit_breaker_config
            )

        # Initialize provider client
        self._initialize_provider_client(name, provider_config)

        self.stats['requests_by_provider'][name] = 0
        logger.info(f"Added provider: {name} (priority={priority})")

    def _initialize_provider_client(self, name: str, config: ProviderConfig):
        """Initialize the actual API client for a provider."""
        try:
            if name == 'groq':
                from groq import Groq
                self.provider_clients[name] = Groq(api_key=config.api_key)
            elif name == 'openai':
                from openai import OpenAI
                self.provider_clients[name] = OpenAI(api_key=config.api_key)
            elif name == 'google':
                import google.generativeai as genai
                genai.configure(api_key=config.api_key)
                self.provider_clients[name] = genai
        except Exception as e:
            logger.warning(f"Failed to initialize {name} client: {e}")

    def enable_mock_mode(self):
        """Enable mock mode for testing without API calls."""
        self.mock_mode = True
        logger.info("Mock mode enabled")

    def get_providers_by_priority(self) -> List[str]:
        """Get provider names sorted by priority."""
        return sorted(
            self.providers.keys(),
            key=lambda x: self.providers[x].priority
        )

    def _call_provider(
        self,
        provider_name: str,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        stream: bool = False
    ) -> Dict:
        """
        Call a specific provider.
        """
        if self.mock_mode:
            time.sleep(0.1)  # Simulate latency
            return {
                'content': self.MOCK_RESPONSES['default'],
                'model': model,
                'provider': provider_name,
                'input_tokens': 50,
                'output_tokens': 20000,
                'total_tokens': 70,
                'is_mock': True
            }

        client = self.provider_clients.get(provider_name)
        if not client:
            raise ProviderUnavailableError(f"No client for provider: {provider_name}")

        if provider_name in ['groq', 'openai']:
            return self._call_openai_compatible(
                client, model, messages, temperature, max_tokens, stream, provider_name
            )
        elif provider_name == 'google':
            return self._call_google(model, messages, temperature, max_tokens)
        else:
            raise ProviderUnavailableError(f"Unknown provider type: {provider_name}")

    def _call_openai_compatible(
        self,
        client,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        stream: bool,
        provider_name: str
    ) -> Dict:
        """Call OpenAI-compatible API (OpenAI, Groq)."""
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )

        if stream:
            content = self.streaming_handler.stream_response_sync(response)
            return {
                'content': content,
                'model': model,
                'provider': provider_name,
                'input_tokens': 0,
                'output_tokens': len(content.split()),
                'total_tokens': len(content.split()),
                'streamed': True
            }
        else:
            return {
                'content': response.choices[0].message.content,
                'model': model,
                'provider': provider_name,
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }

    def _call_google(
        self,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> Dict:
        """Call Google AI API."""
        import google.generativeai as genai

        google_model = genai.GenerativeModel(model)

        # Convert messages
        prompt_parts = []
        for msg in messages:
            prefix = "User: " if msg["role"] == "user" else "Assistant: "
            if msg["role"] == "system":
                prefix = "System: "
            prompt_parts.append(f"{prefix}{msg['content']}")
        prompt = "\n\n".join(prompt_parts)

        response = google_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )

        return {
            'content': response.text,
            'model': model,
            'provider': 'google',
            'input_tokens': int(len(prompt.split()) * 1.3),
            'output_tokens': int(len(response.text.split()) * 1.3),
            'total_tokens': int((len(prompt.split()) + len(response.text.split())) * 1.3)
        }

    def chat(
        self,
        messages: List[Dict],
        model: str = None,
        provider: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        use_cache: bool = True
    ) -> Dict:
        """
        Main chat method with full production features.

        Args:
            messages: List of message dicts
            model: Model to use (optional, uses provider default)
            provider: Specific provider (optional, uses priority order)
            temperature: Sampling temperature
            max_tokens: Max output tokens
            stream: Enable streaming
            use_cache: Check cache first

        Returns:
            Response dict with content and metadata
        """
        start_time = time.time()
        self.stats['total_requests'] += 1

        # Determine providers to try
        if provider:
            providers_to_try = [provider]
        else:
            providers_to_try = self.get_providers_by_priority()

        if not providers_to_try and not self.mock_mode:
            # Fall back to mock mode
            self.mock_mode = True
            providers_to_try = ['mock']

        # Resolve model
        if not model and providers_to_try:
            first_provider = providers_to_try[0]
            if first_provider in self.providers:
                model = self.providers[first_provider].default_model
            else:
                model = 'mock-model'

        # Check cache
        if use_cache and not stream:
            cached = self.cache.get(model, messages, temperature, max_tokens)
            if cached:
                self.stats['cached_responses'] += 1
                self.stats['successful_requests'] += 1
                elapsed = (time.time() - start_time) * 1000
                cached['elapsed_ms'] = elapsed
                self._record_request(cached, elapsed, from_cache=True)
                return cached

        # Try providers
        last_error = None
        for provider_name in providers_to_try:
            try:
                # Check circuit breaker
                if provider_name in self.circuit_breakers:
                    self.circuit_breakers[provider_name].can_execute()

                # Resolve model for this provider
                provider_model = model
                if provider_name in self.providers and not model:
                    provider_model = self.providers[provider_name].default_model

                # Make the call with retry
                result = self._call_with_retry(
                    provider_name, provider_model or 'default',
                    messages, temperature, max_tokens, stream
                )

                # Record success
                if provider_name in self.circuit_breakers:
                    self.circuit_breakers[provider_name].record_success()

                # Update stats
                elapsed = (time.time() - start_time) * 1000
                result['elapsed_ms'] = elapsed
                self.stats['successful_requests'] += 1
                self.stats['total_latency_ms'] += elapsed
                self.stats['total_tokens'] += result.get('total_tokens', 0)
                self.stats['requests_by_provider'][provider_name] = \
                    self.stats['requests_by_provider'].get(provider_name, 0) + 1

                # Cache response
                if use_cache and not stream:
                    self.cache.set(provider_model, messages, temperature, max_tokens, result)

                self._record_request(result, elapsed)
                return result

            except CircuitBreakerOpenError:
                logger.warning(f"Circuit breaker open for {provider_name}, trying next")
                self.stats['fallback_used'] += 1
                continue

            except NON_RETRYABLE_EXCEPTIONS as e:
                # Don't try other providers for auth/request errors
                logger.error(f"Non-retryable error from {provider_name}: {e}")
                raise

            except Exception as e:
                last_error = e
                if provider_name in self.circuit_breakers:
                    self.circuit_breakers[provider_name].record_failure()
                logger.warning(f"Provider {provider_name} failed: {e}")
                self.stats['fallback_used'] += 1
                continue

        # All providers failed
        self.stats['failed_requests'] += 1
        raise ProviderUnavailableError(
            f"All providers failed. Last error: {last_error}"
        )

    def _call_with_retry(
        self,
        provider_name: str,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> Dict:
        """
        Call provider with retry logic.
        """
        @self.retry_handler.create_retry_decorator()
        def make_call():
            return self._call_provider(
                provider_name, model, messages,
                temperature, max_tokens, stream
            )

        return make_call()

    def _record_request(self, result: Dict, elapsed_ms: float, from_cache: bool = False):
        """Record request for monitoring."""
        self.request_history.append({
            'timestamp': time.time(),
            'provider': result.get('provider'),
            'model': result.get('model'),
            'elapsed_ms': elapsed_ms,
            'tokens': result.get('total_tokens', 0),
            'from_cache': from_cache,
            'success': True
        })

    def get_stats(self) -> Dict:
        """Get comprehensive statistics."""
        avg_latency = 0
        if self.stats['successful_requests'] > 0:
            avg_latency = self.stats['total_latency_ms'] / self.stats['successful_requests']

        return {
            **self.stats,
            'avg_latency_ms': round(avg_latency, 2),
            'cache_stats': self.cache.get_stats(),
            'circuit_breaker_status': {
                name: cb.get_status()
                for name, cb in self.circuit_breakers.items()
            }
        }







# Create production client
production_client = ProductionLLMClient(ProductionClientConfig(
    retry_config=RetryConfig(max_attempts=3, min_wait=0.5, max_wait=10.0),
    cache_config=CacheConfig(enabled=True, ttl=300),
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=3, timeout=30.0),
    enable_fallback=True,
    enable_circuit_breaker=True
))

# Add configured providers
if 'groq' in configured_providers:
    production_client.add_provider(
        name='groq',
        api_key=configured_providers['groq']['api_key'],
        default_model='openai/gpt-oss-120b',
        priority=1
    )

if 'google' in configured_providers:
    production_client.add_provider(
        name='google',
        api_key=configured_providers['google']['api_key'],
        default_model='gemini-3-flash-preview',
        priority=2
    )

if 'openai' in configured_providers:
    production_client.add_provider(
        name='openai',
        api_key=configured_providers['openai']['api_key'],
        default_model='gpt-4o-mini',
        priority=3
    )
