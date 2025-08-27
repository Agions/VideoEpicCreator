"""
Enhanced AI Manager for VideoEpicCreator

This module provides an enhanced AI service manager with advanced features including
provider management, load balancing, caching, and intelligent routing.
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Union, AsyncGenerator, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
import statistics

from ..core.base import BaseComponent, ComponentConfig, ComponentState
from ..core.service_container import ServiceContainer, get_service_container, ServiceLifetime
from ..core.events import EventSystem, get_event_system, Event, EventPriority
from .providers import AIProvider, AIProviderInterface, AIRequest, AIResponse, ContentType
from ..config.settings import Settings


class AIProviderState(Enum):
    """AI provider states"""
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    FASTEST_RESPONSE = "fastest_response"
    COST_BASED = "cost_based"
    QUALITY_BASED = "quality_based"


@dataclass
class ProviderMetrics:
    """AI provider performance metrics"""
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_response_time: float = 0.0
    average_response_time: float = 0.0
    total_tokens_used: int = 0
    average_tokens_per_request: float = 0.0
    cost_per_request: float = 0.0
    quality_score: float = 0.0  # 0.0 to 1.0
    last_request_time: float = 0.0
    consecutive_errors: int = 0
    health_score: float = 1.0  # 0.0 to 1.0
    
    def update_metrics(self, response: AIResponse, response_time: float):
        """Update metrics with response data"""
        self.request_count += 1
        self.total_response_time += response_time
        self.average_response_time = self.total_response_time / self.request_count
        
        if response.error:
            self.error_count += 1
            self.consecutive_errors += 1
        else:
            self.success_count += 1
            self.consecutive_errors = 0
            self.total_tokens_used += response.tokens_used
            self.average_tokens_per_request = self.total_tokens_used / self.success_count
        
        self.last_request_time = time.time()
        self._update_health_score()
    
    def _update_health_score(self):
        """Update health score based on metrics"""
        if self.request_count == 0:
            self.health_score = 1.0
            return
        
        # Calculate health score components
        success_rate = self.success_count / self.request_count
        error_penalty = min(0.5, self.consecutive_errors * 0.1)
        latency_score = max(0.0, 1.0 - (self.average_response_time / 30.0))  # 30s timeout
        
        # Weighted health score
        self.health_score = (success_rate * 0.5 + latency_score * 0.3 + self.quality_score * 0.2) - error_penalty
        self.health_score = max(0.0, min(1.0, self.health_score))


@dataclass
class ProviderConfig:
    """AI provider configuration"""
    provider: AIProvider
    enabled: bool = True
    weight: int = 1  # For weighted load balancing
    max_concurrent_requests: int = 10
    request_timeout: int = 60
    retry_attempts: int = 3
    cost_per_token: float = 0.0
    quality_threshold: float = 0.7
    maintenance_mode: bool = False
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheEntry:
    """Cache entry for AI responses"""
    request_hash: str
    response: AIResponse
    timestamp: float
    ttl: float  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.timestamp > self.ttl


class AIRequestRouter:
    """AI request router for intelligent provider selection"""
    
    def __init__(self, ai_manager: 'EnhancedAIManager'):
        self.ai_manager = ai_manager
        self._logger = logging.getLogger("ai_request_router")
        self._request_history = defaultdict(lambda: deque(maxlen=100))
        self._current_weights = {}
    
    def select_provider(self, request: AIRequest, strategy: LoadBalancingStrategy) -> AIProvider:
        """Select the best provider for the request"""
        available_providers = self._get_available_providers()
        
        if not available_providers:
            raise RuntimeError("No available AI providers")
        
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(available_providers)
        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_selection(available_providers)
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(available_providers)
        elif strategy == LoadBalancingStrategy.FASTEST_RESPONSE:
            return self._fastest_response_selection(available_providers)
        elif strategy == LoadBalancingStrategy.COST_BASED:
            return self._cost_based_selection(available_providers, request)
        elif strategy == LoadBalancingStrategy.QUALITY_BASED:
            return self._quality_based_selection(available_providers, request)
        else:
            return available_providers[0]
    
    def _get_available_providers(self) -> List[AIProvider]:
        """Get list of available providers"""
        return [
            provider for provider, config in self.ai_manager.provider_configs.items()
            if (config.enabled and 
                not config.maintenance_mode and
                self.ai_manager.get_provider_state(provider) == AIProviderState.AVAILABLE)
        ]
    
    def _round_robin_selection(self, providers: List[AIProvider]) -> AIProvider:
        """Round robin provider selection"""
        if not hasattr(self, '_round_robin_index'):
            self._round_robin_index = 0
        
        provider = providers[self._round_robin_index % len(providers)]
        self._round_robin_index += 1
        return provider
    
    def _weighted_round_robin_selection(self, providers: List[AIProvider]) -> AIProvider:
        """Weighted round robin provider selection"""
        total_weight = sum(
            self.ai_manager.provider_configs[provider].weight 
            for provider in providers
        )
        
        if total_weight == 0:
            return providers[0]
        
        current_weight = getattr(self, '_current_weight', 0)
        self._current_weight = (current_weight + 1) % total_weight
        
        cumulative_weight = 0
        for provider in providers:
            cumulative_weight += self.ai_manager.provider_configs[provider].weight
            if current_weight < cumulative_weight:
                return provider
        
        return providers[-1]
    
    def _least_connections_selection(self, providers: List[AIProvider]) -> AIProvider:
        """Least connections provider selection"""
        active_requests = self.ai_manager.get_active_requests_count()
        
        if not active_requests:
            return providers[0]
        
        # Find provider with least active requests
        provider_loads = [
            (provider, active_requests.get(provider, 0))
            for provider in providers
        ]
        
        return min(provider_loads, key=lambda x: x[1])[0]
    
    def _fastest_response_selection(self, providers: List[AIProvider]) -> AIProvider:
        """Fastest response time provider selection"""
        response_times = {
            provider: self.ai_manager.provider_metrics[provider].average_response_time
            for provider in providers
        }
        
        return min(response_times, key=response_times.get)
    
    def _cost_based_selection(self, providers: List[AIProvider], request: AIRequest) -> AIProvider:
        """Cost-based provider selection"""
        estimated_costs = {}
        
        for provider in providers:
            config = self.ai_manager.provider_configs[provider]
            metrics = self.ai_manager.provider_metrics[provider]
            
            # Estimate cost based on tokens and provider rates
            estimated_tokens = request.max_tokens
            estimated_cost = estimated_tokens * config.cost_per_token
            
            # Adjust for reliability (higher cost for less reliable providers)
            reliability_factor = metrics.health_score
            adjusted_cost = estimated_cost / reliability_factor if reliability_factor > 0 else float('inf')
            
            estimated_costs[provider] = adjusted_cost
        
        return min(estimated_costs, key=estimated_costs.get)
    
    def _quality_based_selection(self, providers: List[AIProvider], request: AIRequest) -> AIProvider:
        """Quality-based provider selection"""
        quality_scores = {}
        
        for provider in providers:
            config = self.ai_manager.provider_configs[provider]
            metrics = self.ai_manager.provider_metrics[provider]
            
            # Calculate quality score based on various factors
            health_score = metrics.health_score
            quality_threshold = config.quality_threshold
            
            # Consider content type specialization
            type_bonus = self._get_type_specialization_bonus(provider, request.content_type)
            
            final_score = health_score * 0.7 + type_bonus * 0.3
            quality_scores[provider] = final_score
        
        return max(quality_scores, key=quality_scores.get)
    
    def _get_type_specialization_bonus(self, provider: AIProvider, content_type: ContentType) -> float:
        """Get specialization bonus for content type"""
        # This could be based on historical performance for specific content types
        return 0.5  # Default bonus


class AICache:
    """AI response caching system"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger("ai_cache")
    
    def get(self, request: AIRequest) -> Optional[AIResponse]:
        """Get cached response for request"""
        cache_key = self._generate_cache_key(request)
        
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if not entry.is_expired():
                    self._logger.debug(f"Cache hit for request: {cache_key}")
                    return entry.response
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
        
        return None
    
    def put(self, request: AIRequest, response: AIResponse, ttl: Optional[float] = None):
        """Cache response for request"""
        if response.error:
            return  # Don't cache error responses
        
        cache_key = self._generate_cache_key(request)
        cache_ttl = ttl or self.default_ttl
        
        with self._lock:
            # Remove oldest entries if cache is full
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys(), 
                                key=lambda k: self._cache[k].timestamp)
                del self._cache[oldest_key]
            
            # Add new entry
            entry = CacheEntry(
                request_hash=cache_key,
                response=response,
                timestamp=time.time(),
                ttl=cache_ttl
            )
            self._cache[cache_key] = entry
            
            self._logger.debug(f"Cached response for request: {cache_key}")
    
    def clear(self):
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()
        self._logger.info("AI cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": self._calculate_hit_rate(),
                "expired_entries": len([e for e in self._cache.values() if e.is_expired()])
            }
    
    def _generate_cache_key(self, request: AIRequest) -> str:
        """Generate cache key for request"""
        key_data = {
            "prompt": request.prompt,
            "content_type": request.content_type.value,
            "provider": request.provider.value,
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate (simplified)"""
        # This would need to track hits and misses over time
        return 0.0


class EnhancedAIManager(BaseComponent[Dict[str, Any]]):
    """Enhanced AI Manager with advanced features"""
    
    def __init__(self, settings: Settings, config: Optional[ComponentConfig] = None):
        super().__init__("enhanced_ai_manager", config)
        self.settings = settings
        
        # Core components
        self.providers: Dict[AIProvider, AIProviderInterface] = {}
        self.provider_configs: Dict[AIProvider, ProviderConfig] = {}
        self.provider_metrics: Dict[AIProvider, ProviderMetrics] = {}
        self.provider_states: Dict[AIProvider, AIProviderState] = {}
        
        # Advanced features
        self.request_router = AIRequestRouter(self)
        self.cache = AICache()
        self.active_requests: Dict[AIProvider, int] = defaultdict(int)
        self.request_history = deque(maxlen=1000)
        
        # Configuration
        self.load_balancing_strategy = LoadBalancingStrategy.QUALITY_BASED
        self.enable_caching = True
        self.enable_load_balancing = True
        self.max_concurrent_requests = 50
        
        # Threading
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._lock = threading.RLock()
        
        # Services
        self._event_system = get_event_system()
        self._service_container = get_service_container()
        
        self._logger = logging.getLogger("enhanced_ai_manager")
    
    async def initialize(self) -> bool:
        """Initialize the enhanced AI manager"""
        try:
            self.logger.info("Initializing Enhanced AI Manager")
            
            # Initialize providers
            await self._initialize_providers()
            
            # Start health monitoring
            self._start_health_monitoring()
            
            # Start cache cleanup
            self._start_cache_cleanup()
            
            # Register with service container
            self._service_container.register(EnhancedAIManager, EnhancedAIManager, 
                                            ServiceLifetime.SINGLETON)
            self._service_container._service_instances["EnhancedAIManager"] = self
            
            self.set_state(ComponentState.RUNNING)
            return True
        
        except Exception as e:
            self.handle_error(e, "initialize")
            return False
    
    async def start(self) -> bool:
        """Start the enhanced AI manager"""
        try:
            # Validate provider connections
            await self._validate_all_providers()
            
            # Load provider configurations
            await self._load_provider_configs()
            
            self.set_state(ComponentState.RUNNING)
            return True
        
        except Exception as e:
            self.handle_error(e, "start")
            return False
    
    async def stop(self) -> bool:
        """Stop the enhanced AI manager"""
        try:
            # Stop health monitoring
            self._stop_health_monitoring()
            
            # Wait for active requests to complete
            await self._wait_for_active_requests()
            
            self.set_state(ComponentState.STOPPED)
            return True
        
        except Exception as e:
            self.handle_error(e, "stop")
            return False
    
    async def cleanup(self) -> bool:
        """Clean up enhanced AI manager resources"""
        try:
            # Clear cache
            self.cache.clear()
            
            # Clear providers
            self.providers.clear()
            self.provider_configs.clear()
            self.provider_metrics.clear()
            self.provider_states.clear()
            
            # Shutdown executor
            self._executor.shutdown(wait=True)
            
            self.set_state(ComponentState.STOPPED)
            return True
        
        except Exception as e:
            self.handle_error(e, "cleanup")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get enhanced AI manager status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "providers": {
                provider.value: {
                    "state": state.value,
                    "metrics": metrics.__dict__,
                    "config": config.__dict__,
                    "active_requests": self.active_requests.get(provider, 0)
                }
                for provider, state, metrics, config in zip(
                    self.provider_states.keys(),
                    self.provider_states.values(),
                    self.provider_metrics.values(),
                    self.provider_configs.values()
                )
            },
            "cache_stats": self.cache.get_stats(),
            "load_balancing": {
                "strategy": self.load_balancing_strategy.value,
                "active_requests": dict(self.active_requests)
            },
            "statistics": {
                "total_requests": sum(m.request_count for m in self.provider_metrics.values()),
                "total_tokens": sum(m.total_tokens_used for m in self.provider_metrics.values()),
                "average_response_time": statistics.mean(
                    [m.average_response_time for m in self.provider_metrics.values() if m.request_count > 0]
                ) if self.provider_metrics else 0.0,
                "overall_success_rate": self._calculate_overall_success_rate()
            },
            "metrics": self.metrics.__dict__
        }
    
    async def _initialize_providers(self):
        """Initialize AI providers based on settings"""
        ai_settings = self.settings.get_ai_settings()
        
        # Initialize OpenAI provider
        if ai_settings.openai_api_key:
            from .providers import OpenAIProvider
            self.providers[AIProvider.OPENAI] = OpenAIProvider(ai_settings.openai_api_key)
            self.provider_configs[AIProvider.OPENAI] = ProviderConfig(
                provider=AIProvider.OPENAI,
                weight=3,
                cost_per_token=0.002,  # $0.002 per 1K tokens
                quality_threshold=0.8
            )
        
        # Initialize Qianwen provider
        if ai_settings.qianwen_api_key:
            from .providers import QianwenProvider
            self.providers[AIProvider.QIANWEN] = QianwenProvider(ai_settings.qianwen_api_key)
            self.provider_configs[AIProvider.QIANWEN] = ProviderConfig(
                provider=AIProvider.QIANWEN,
                weight=2,
                cost_per_token=0.001,  # $0.001 per 1K tokens
                quality_threshold=0.7
            )
        
        # Initialize Ollama provider
        from .providers import OllamaProvider
        self.providers[AIProvider.OLLAMA] = OllamaProvider(ai_settings.ollama_base_url)
        self.provider_configs[AIProvider.OLLAMA] = ProviderConfig(
            provider=AIProvider.OLLAMA,
            weight=1,
            cost_per_token=0.0,  # Free for local models
            quality_threshold=0.6
        )
        
        # Initialize metrics and states
        for provider in self.providers:
            self.provider_metrics[provider] = ProviderMetrics()
            self.provider_states[provider] = AIProviderState.UNKNOWN
    
    async def _validate_all_providers(self):
        """Validate all provider connections"""
        validation_tasks = []
        
        for provider, instance in self.providers.items():
            task = asyncio.create_task(self._validate_provider(provider))
            validation_tasks.append(task)
        
        await asyncio.gather(*validation_tasks, return_exceptions=True)
    
    async def _validate_provider(self, provider: AIProvider):
        """Validate a specific provider"""
        try:
            instance = self.providers[provider]
            is_valid = instance.validate_api_key()
            
            if is_valid:
                self.provider_states[provider] = AIProviderState.AVAILABLE
                self.logger.info(f"{provider.value} provider is available")
            else:
                self.provider_states[provider] = AIProviderState.UNAVAILABLE
                self.logger.warning(f"{provider.value} provider is not available")
            
            # Emit event
            self._event_system.emit("provider_validated", {
                "provider": provider.value,
                "available": is_valid
            })
        
        except Exception as e:
            self.provider_states[provider] = AIProviderState.UNAVAILABLE
            self.logger.error(f"Error validating {provider.value} provider: {e}")
    
    async def _load_provider_configs(self):
        """Load provider configurations from settings"""
        # This could load from database or configuration files
        pass
    
    def _start_health_monitoring(self):
        """Start health monitoring for providers"""
        # Start background health check task
        asyncio.create_task(self._health_monitor_loop())
    
    def _stop_health_monitoring(self):
        """Stop health monitoring"""
        # This would cancel the health monitoring task
        pass
    
    async def _health_monitor_loop(self):
        """Health monitoring loop"""
        while self.state == ComponentState.RUNNING:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _perform_health_checks(self):
        """Perform health checks on all providers"""
        for provider, instance in self.providers.items():
            try:
                # Simple health check - could be more sophisticated
                is_healthy = instance.validate_api_key()
                
                if is_healthy:
                    if self.provider_states[provider] != AIProviderState.AVAILABLE:
                        self.provider_states[provider] = AIProviderState.AVAILABLE
                        self._event_system.emit("provider_recovered", {
                            "provider": provider.value
                        })
                else:
                    if self.provider_states[provider] == AIProviderState.AVAILABLE:
                        self.provider_states[provider] = AIProviderState.UNAVAILABLE
                        self._event_system.emit("provider_failed", {
                            "provider": provider.value
                        })
            
            except Exception as e:
                self.logger.error(f"Health check failed for {provider.value}: {e}")
                self.provider_states[provider] = AIProviderState.UNAVAILABLE
    
    def _start_cache_cleanup(self):
        """Start cache cleanup task"""
        asyncio.create_task(self._cache_cleanup_loop())
    
    async def _cache_cleanup_loop(self):
        """Cache cleanup loop"""
        while self.state == ComponentState.RUNNING:
            try:
                await self._cleanup_expired_cache_entries()
                await asyncio.sleep(300)  # Clean every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_expired_cache_entries(self):
        """Clean up expired cache entries"""
        # This is handled automatically by the cache get method
        pass
    
    async def _wait_for_active_requests(self):
        """Wait for active requests to complete"""
        max_wait_time = 30  # seconds
        wait_start = time.time()
        
        while sum(self.active_requests.values()) > 0:
            if time.time() - wait_start > max_wait_time:
                self.logger.warning("Timeout waiting for active requests to complete")
                break
            
            await asyncio.sleep(0.1)
    
    def get_provider_state(self, provider: AIProvider) -> AIProviderState:
        """Get provider state"""
        return self.provider_states.get(provider, AIProviderState.UNKNOWN)
    
    def get_active_requests_count(self) -> Dict[AIProvider, int]:
        """Get active requests count per provider"""
        return dict(self.active_requests)
    
    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate"""
        total_requests = sum(m.request_count for m in self.provider_metrics.values())
        total_successes = sum(m.success_count for m in self.provider_metrics.values())
        
        if total_requests == 0:
            return 0.0
        
        return total_successes / total_requests
    
    # Enhanced AI generation methods
    async def generate_content_enhanced(
        self,
        prompt: str,
        content_type: ContentType,
        provider: Optional[AIProvider] = None,
        model: Optional[str] = None,
        use_cache: bool = True,
        strategy: Optional[LoadBalancingStrategy] = None,
        **kwargs
    ) -> AIResponse:
        """Generate content with enhanced features"""
        if not self.is_ready():
            raise RuntimeError("AI Manager is not ready")
        
        start_time = time.time()
        
        # Check cache first
        if use_cache and self.enable_caching:
            cached_response = self.cache.get(AIRequest(
                prompt=prompt,
                content_type=content_type,
                provider=provider or AIProvider.OPENAI,
                model=model or "default",
                **kwargs
            ))
            
            if cached_response:
                self.logger.debug("Returning cached response")
                return cached_response
        
        # Select provider
        if provider is None:
            strategy = strategy or self.load_balancing_strategy
            provider = self.request_router.select_provider(
                AIRequest(prompt=prompt, content_type=content_type, 
                         provider=AIProvider.OPENAI, **kwargs),
                strategy
            )
        
        if provider not in self.providers:
            raise ValueError(f"Provider {provider.value} not available")
        
        # Check concurrency limits
        config = self.provider_configs[provider]
        if self.active_requests[provider] >= config.max_concurrent_requests:
            self.logger.warning(f"Provider {provider.value} is at capacity")
            # Could implement queuing or fallback here
            raise RuntimeError(f"Provider {provider.value} is at capacity")
        
        # Execute request
        self.active_requests[provider] += 1
        
        try:
            # Get model
            if model is None:
                available_models = self.providers[provider].get_available_models()
                model = available_models[0] if available_models else "default"
            
            # Create request
            request = AIRequest(
                prompt=prompt,
                content_type=content_type,
                provider=provider,
                model=model,
                **kwargs
            )
            
            # Generate content
            response = await self.providers[provider].generate_content(request)
            response_time = time.time() - start_time
            
            # Update metrics
            self.provider_metrics[provider].update_metrics(response, response_time)
            
            # Cache successful responses
            if use_cache and self.enable_caching and not response.error:
                self.cache.put(request, response)
            
            # Update metrics
            self.update_metrics(response_time)
            
            # Emit event
            self._event_system.emit("ai_content_generated", {
                "provider": provider.value,
                "content_type": content_type.value,
                "success": not response.error,
                "response_time": response_time,
                "tokens_used": response.tokens_used
            })
            
            return response
        
        except Exception as e:
            # Update error metrics
            self.provider_metrics[provider].error_count += 1
            
            # Emit error event
            self._event_system.emit("ai_content_generation_error", {
                "provider": provider.value,
                "content_type": content_type.value,
                "error": str(e)
            })
            
            self.handle_error(e, "generate_content_enhanced")
            raise
        
        finally:
            self.active_requests[provider] -= 1
    
    async def generate_stream_enhanced(
        self,
        prompt: str,
        content_type: ContentType,
        provider: Optional[AIProvider] = None,
        model: Optional[str] = None,
        strategy: Optional[LoadBalancingStrategy] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming content with enhanced features"""
        if not self.is_ready():
            raise RuntimeError("AI Manager is not ready")
        
        # Select provider
        if provider is None:
            strategy = strategy or self.load_balancing_strategy
            provider = self.request_router.select_provider(
                AIRequest(prompt=prompt, content_type=content_type, 
                         provider=AIProvider.OPENAI, **kwargs),
                strategy
            )
        
        if provider not in self.providers:
            raise ValueError(f"Provider {provider.value} not available")
        
        # Get model
        if model is None:
            available_models = self.providers[provider].get_available_models()
            model = available_models[0] if available_models else "default"
        
        # Create request
        request = AIRequest(
            prompt=prompt,
            content_type=content_type,
            provider=provider,
            model=model,
            stream=True,
            **kwargs
        )
        
        # Generate streaming content
        start_time = time.time()
        self.active_requests[provider] += 1
        
        try:
            async for chunk in self.providers[provider].generate_stream(request):
                yield chunk
        
        except Exception as e:
            self.handle_error(e, "generate_stream_enhanced")
            raise
        
        finally:
            self.active_requests[provider] -= 1
    
    def get_provider_recommendations(self, content_type: ContentType, 
                                   requirements: Dict[str, Any]) -> List[AIProvider]:
        """Get recommended providers for specific requirements"""
        recommendations = []
        
        for provider, config in self.provider_configs.items():
            if not config.enabled or config.maintenance_mode:
                continue
            
            metrics = self.provider_metrics[provider]
            
            # Score provider based on requirements
            score = 0.0
            
            # Health score
            score += metrics.health_score * 0.3
            
            # Quality threshold
            if metrics.quality_score >= config.quality_threshold:
                score += 0.2
            
            # Cost efficiency
            if requirements.get("cost_sensitive", False):
                cost_score = 1.0 - min(1.0, config.cost_per_token * 100)
                score += cost_score * 0.2
            
            # Performance requirements
            if requirements.get("low_latency", False):
                latency_score = 1.0 - min(1.0, metrics.average_response_time / 10.0)
                score += latency_score * 0.2
            
            # Specialization
            if requirements.get("high_quality", False):
                quality_score = metrics.quality_score
                score += quality_score * 0.1
            
            recommendations.append((provider, score))
        
        # Sort by score and return providers
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return [provider for provider, score in recommendations]
    
    def get_provider_statistics(self, provider: AIProvider) -> Dict[str, Any]:
        """Get detailed statistics for a provider"""
        if provider not in self.provider_metrics:
            return {}
        
        metrics = self.provider_metrics[provider]
        config = self.provider_configs.get(provider)
        
        return {
            "provider": provider.value,
            "state": self.provider_states[provider].value,
            "metrics": metrics.__dict__,
            "config": config.__dict__ if config else {},
            "performance_analysis": {
                "success_rate": metrics.success_count / max(1, metrics.request_count),
                "average_latency": metrics.average_response_time,
                "cost_efficiency": metrics.total_tokens_used * (config.cost_per_token if config else 0),
                "quality_trend": self._calculate_quality_trend(provider)
            }
        }
    
    def _calculate_quality_trend(self, provider: AIProvider) -> str:
        """Calculate quality trend for a provider"""
        # This would analyze historical quality data
        return "stable"  # Placeholder
    
    async def optimize_provider_configs(self):
        """Optimize provider configurations based on performance"""
        # This would automatically adjust weights and settings
        # based on historical performance data
        pass
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for analysis"""
        return {
            "timestamp": time.time(),
            "providers": {
                provider.value: metrics.__dict__
                for provider, metrics in self.provider_metrics.items()
            },
            "cache": self.cache.get_stats(),
            "system": {
                "total_requests": sum(m.request_count for m in self.provider_metrics.values()),
                "total_tokens": sum(m.total_tokens_used for m in self.provider_metrics.values()),
                "overall_success_rate": self._calculate_overall_success_rate()
            }
        }