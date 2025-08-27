"""
Video Processing Pipeline Data Flow Architecture

This module provides a comprehensive data flow architecture for video processing
with pipeline stages, data validation, flow control, and performance monitoring.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union, AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import json
from pathlib import Path

from ..core.base import BaseComponent, ComponentConfig, ComponentState
from ..core.events import EventSystem, get_event_system, Event, EventPriority
from ..core.video_engine import VideoProcessor, VideoInfo, Scene, TimelineSegment
from ..config.settings import Settings


class PipelineStage(Enum):
    """Pipeline processing stages"""
    INPUT_VALIDATION = "input_validation"
    VIDEO_ANALYSIS = "video_analysis"
    SCENE_DETECTION = "scene_detection"
    CONTENT_GENERATION = "content_generation"
    TIMELINE_SYNCHRONIZATION = "timeline_synchronization"
    POST_PROCESSING = "post_processing"
    OUTPUT_GENERATION = "output_generation"
    QUALITY_ASSURANCE = "quality_assurance"


class PipelineState(Enum):
    """Pipeline execution states"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataFlowDirection(Enum):
    """Data flow directions"""
    FORWARD = "forward"          # Normal forward flow
    BACKWARD = "backward"        # Backward for error recovery
    PARALLEL = "parallel"        # Parallel processing
    BRANCHING = "branching"      # Branching for multiple paths


@dataclass
class PipelineData:
    """Data structure for pipeline processing"""
    data_id: str
    stage: PipelineStage
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source_stage: Optional[PipelineStage] = None
    quality_score: float = 0.0
    processing_time: float = 0.0
    error_info: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if data is valid"""
        return self.error_info is None and self.content is not None
    
    def mark_error(self, error: str):
        """Mark data as errored"""
        self.error_info = error
        self.quality_score = 0.0


@dataclass
class PipelineMetrics:
    """Pipeline performance metrics"""
    total_processing_time: float = 0.0
    stages_completed: int = 0
    stages_failed: int = 0
    data_throughput: float = 0.0
    average_stage_time: float = 0.0
    success_rate: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    error_count: int = 0
    warning_count: int = 0


@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    max_concurrent_stages: int = 4
    stage_timeout: float = 300.0  # 5 minutes
    enable_parallel_processing: bool = True
    enable_error_recovery: bool = True
    enable_quality_checks: bool = True
    enable_performance_monitoring: bool = True
    enable_caching: bool = True
    cache_ttl: float = 3600.0  # 1 hour
    retry_attempts: int = 3
    batch_size: int = 10
    memory_limit_mb: int = 2048


class PipelineStageProcessor(ABC):
    """Abstract base class for pipeline stage processors"""
    
    def __init__(self, stage: PipelineStage, config: PipelineConfig):
        self.stage = stage
        self.config = config
        self.logger = logging.getLogger(f"pipeline.{stage.value}")
        self.event_system = get_event_system()
        self.metrics = {
            "processed_count": 0,
            "success_count": 0,
            "error_count": 0,
            "average_processing_time": 0.0
        }
    
    @abstractmethod
    async def process(self, data: PipelineData) -> PipelineData:
        """Process data in this stage"""
        pass
    
    @abstractmethod
    def validate_input(self, data: PipelineData) -> bool:
        """Validate input data for this stage"""
        pass
    
    @abstractmethod
    def validate_output(self, data: PipelineData) -> bool:
        """Validate output data from this stage"""
        pass
    
    async def preprocess(self, data: PipelineData) -> PipelineData:
        """Preprocess data before main processing"""
        return data
    
    async def postprocess(self, data: PipelineData) -> PipelineData:
        """Postprocess data after main processing"""
        return data
    
    def update_metrics(self, processing_time: float, success: bool):
        """Update stage metrics"""
        self.metrics["processed_count"] += 1
        
        if success:
            self.metrics["success_count"] += 1
        else:
            self.metrics["error_count"] += 1
        
        # Update average processing time
        total_time = self.metrics["average_processing_time"] * (self.metrics["processed_count"] - 1)
        total_time += processing_time
        self.metrics["average_processing_time"] = total_time / self.metrics["processed_count"]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get stage metrics"""
        return self.metrics.copy()


class InputValidationProcessor(PipelineStageProcessor):
    """Input validation stage processor"""
    
    def __init__(self, config: PipelineConfig):
        super().__init__(PipelineStage.INPUT_VALIDATION, config)
    
    async def process(self, data: PipelineData) -> PipelineData:
        """Validate input data"""
        start_time = time.time()
        
        try:
            # Validate required fields
            if not hasattr(data, 'content') or data.content is None:
                data.mark_error("Missing content data")
                return data
            
            # Validate video file path if present
            if isinstance(data.content, dict) and "video_path" in data.content:
                video_path = Path(data.content["video_path"])
                if not video_path.exists():
                    data.mark_error(f"Video file not found: {video_path}")
                    return data
                
                # Validate file extension
                valid_extensions = {".mp4", ".avi", ".mov", ".wmv", ".mkv", ".webm"}
                if video_path.suffix.lower() not in valid_extensions:
                    data.mark_error(f"Unsupported video format: {video_path.suffix}")
                    return data
            
            # Update data
            data.stage = PipelineStage.INPUT_VALIDATION
            data.quality_score = 1.0
            
            # Update metrics
            processing_time = time.time() - start_time
            self.update_metrics(processing_time, True)
            
            # Emit event
            self.event_system.emit("input_validated", {
                "data_id": data.data_id,
                "processing_time": processing_time
            })
            
            return data
        
        except Exception as e:
            data.mark_error(f"Input validation failed: {str(e)}")
            processing_time = time.time() - start_time
            self.update_metrics(processing_time, False)
            return data
    
    def validate_input(self, data: PipelineData) -> bool:
        """Validate input for validation stage"""
        return hasattr(data, 'content')
    
    def validate_output(self, data: PipelineData) -> bool:
        """Validate output from validation stage"""
        return data.is_valid() and data.stage == PipelineStage.INPUT_VALIDATION


class VideoAnalysisProcessor(PipelineStageProcessor):
    """Video analysis stage processor"""
    
    def __init__(self, config: PipelineConfig, video_processor: VideoProcessor):
        super().__init__(PipelineStage.VIDEO_ANALYSIS, config)
        self.video_processor = video_processor
    
    async def process(self, data: PipelineData) -> PipelineData:
        """Analyze video content"""
        start_time = time.time()
        
        try:
            if not isinstance(data.content, dict):
                data.mark_error("Invalid content format for video analysis")
                return data
            
            video_path = data.content.get("video_path")
            if not video_path:
                data.mark_error("Missing video path")
                return data
            
            # Get video info
            video_info = await self.video_processor.get_video_info(video_path)
            
            # Analyze video content
            content_analysis = await self.video_processor.analyze_video_content(video_path)
            
            # Update data
            data.content = {
                "video_info": video_info.__dict__,
                "content_analysis": content_analysis,
                "video_path": video_path
            }
            data.stage = PipelineStage.VIDEO_ANALYSIS
            data.quality_score = 0.9
            
            # Update metrics
            processing_time = time.time() - start_time
            self.update_metrics(processing_time, True)
            
            # Emit event
            self.event_system.emit("video_analyzed", {
                "data_id": data.data_id,
                "video_duration": video_info.duration,
                "processing_time": processing_time
            })
            
            return data
        
        except Exception as e:
            data.mark_error(f"Video analysis failed: {str(e)}")
            processing_time = time.time() - start_time
            self.update_metrics(processing_time, False)
            return data
    
    def validate_input(self, data: PipelineData) -> bool:
        """Validate input for video analysis"""
        return (data.is_valid() and 
                isinstance(data.content, dict) and 
                "video_path" in data.content)
    
    def validate_output(self, data: PipelineData) -> bool:
        """Validate output from video analysis"""
        return (data.is_valid() and 
                data.stage == PipelineStage.VIDEO_ANALYSIS and
                isinstance(data.content, dict) and
                "video_info" in data.content)


class SceneDetectionProcessor(PipelineStageProcessor):
    """Scene detection stage processor"""
    
    def __init__(self, config: PipelineConfig, video_processor: VideoProcessor):
        super().__init__(PipelineStage.SCENE_DETECTION, config)
        self.video_processor = video_processor
    
    async def process(self, data: PipelineData) -> PipelineData:
        """Detect scenes in video"""
        start_time = time.time()
        
        try:
            if not isinstance(data.content, dict):
                data.mark_error("Invalid content format for scene detection")
                return data
            
            video_path = data.content.get("video_path")
            if not video_path:
                data.mark_error("Missing video path")
                return data
            
            # Extract scenes
            scenes = await self.video_processor.extract_scenes(video_path)
            
            # Convert to serializable format
            scene_data = [
                {
                    "start_time": scene.start_time,
                    "end_time": scene.end_time,
                    "duration": scene.duration,
                    "frame_count": scene.frame_count,
                    "key_frame_index": scene.key_frame_index,
                    "description": scene.description,
                    "tags": scene.tags,
                    "importance": scene.importance
                }
                for scene in scenes
            ]
            
            # Update data
            data.content["scenes"] = scene_data
            data.stage = PipelineStage.SCENE_DETECTION
            data.quality_score = 0.85
            
            # Update metrics
            processing_time = time.time() - start_time
            self.update_metrics(processing_time, True)
            
            # Emit event
            self.event_system.emit("scenes_detected", {
                "data_id": data.data_id,
                "scene_count": len(scenes),
                "processing_time": processing_time
            })
            
            return data
        
        except Exception as e:
            data.mark_error(f"Scene detection failed: {str(e)}")
            processing_time = time.time() - start_time
            self.update_metrics(processing_time, False)
            return data
    
    def validate_input(self, data: PipelineData) -> bool:
        """Validate input for scene detection"""
        return (data.is_valid() and 
                isinstance(data.content, dict) and 
                "video_path" in data.content)
    
    def validate_output(self, data: PipelineData) -> bool:
        """Validate output from scene detection"""
        return (data.is_valid() and 
                data.stage == PipelineStage.SCENE_DETECTION and
                isinstance(data.content, dict) and
                "scenes" in data.content)


class VideoProcessingPipeline(BaseComponent[Dict[str, Any]]):
    """Main video processing pipeline"""
    
    def __init__(self, settings: Settings, video_processor: VideoProcessor, 
                 config: Optional[PipelineConfig] = None):
        super().__init__("video_processing_pipeline", config)
        self.settings = settings
        self.video_processor = video_processor
        self.config = config or PipelineConfig()
        
        # Pipeline components
        self.stages: Dict[PipelineStage, PipelineStageProcessor] = {}
        self.pipeline_state = PipelineState.IDLE
        self.active_processes: Dict[str, asyncio.Task] = {}
        self.data_queue: asyncio.Queue = asyncio.Queue()
        self.completed_data: Dict[str, PipelineData] = {}
        
        # Metrics and monitoring
        self.pipeline_metrics = PipelineMetrics()
        self.stage_metrics: Dict[PipelineStage, Dict[str, Any]] = {}
        
        # Threading and execution
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_stages)
        self._lock = threading.RLock()
        
        # Services
        self._event_system = get_event_system()
        self._logger = logging.getLogger("video_processing_pipeline")
        
        # Initialize stages
        self._initialize_stages()
    
    def _initialize_stages(self):
        """Initialize pipeline stage processors"""
        self.stages[PipelineStage.INPUT_VALIDATION] = InputValidationProcessor(self.config)
        self.stages[PipelineStage.VIDEO_ANALYSIS] = VideoAnalysisProcessor(self.config, self.video_processor)
        self.stages[PipelineStage.SCENE_DETECTION] = SceneDetectionProcessor(self.config, self.video_processor)
    
    async def initialize(self) -> bool:
        """Initialize the pipeline"""
        try:
            self.logger.info("Initializing Video Processing Pipeline")
            
            # Validate all stages
            for stage, processor in self.stages.items():
                self.logger.info(f"Initialized stage: {stage.value}")
            
            self.set_state(ComponentState.RUNNING)
            return True
        
        except Exception as e:
            self.handle_error(e, "initialize")
            return False
    
    async def start(self) -> bool:
        """Start the pipeline"""
        try:
            self.pipeline_state = PipelineState.IDLE
            self.logger.info("Video Processing Pipeline started")
            return True
        
        except Exception as e:
            self.handle_error(e, "start")
            return False
    
    async def stop(self) -> bool:
        """Stop the pipeline"""
        try:
            # Cancel all active processes
            for process_id, task in self.active_processes.items():
                task.cancel()
                self.logger.info(f"Cancelled process: {process_id}")
            
            self.active_processes.clear()
            
            # Clear queues
            while not self.data_queue.empty():
                await self.data_queue.get()
            
            self.pipeline_state = PipelineState.IDLE
            self.logger.info("Video Processing Pipeline stopped")
            return True
        
        except Exception as e:
            self.handle_error(e, "stop")
            return False
    
    async def cleanup(self) -> bool:
        """Clean up pipeline resources"""
        try:
            await self.stop()
            
            # Clear data
            self.completed_data.clear()
            
            # Shutdown executor
            self._executor.shutdown(wait=True)
            
            self.logger.info("Video Processing Pipeline cleaned up")
            return True
        
        except Exception as e:
            self.handle_error(e, "cleanup")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "pipeline_state": self.pipeline_state.value,
            "active_processes": len(self.active_processes),
            "queue_size": self.data_queue.qsize(),
            "completed_items": len(self.completed_data),
            "pipeline_metrics": self.pipeline_metrics.__dict__,
            "stage_metrics": {stage.value: metrics for stage, metrics in self.stage_metrics.items()},
            "config": self.config.__dict__,
            "metrics": self.metrics.__dict__
        }
    
    async def process_video(self, video_path: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Process a video through the pipeline"""
        if self.pipeline_state != PipelineState.IDLE:
            raise RuntimeError("Pipeline is not ready")
        
        # Create initial data
        data_id = f"video_{int(time.time())}_{hash(video_path) % 10000}"
        
        initial_data = PipelineData(
            data_id=data_id,
            stage=PipelineStage.INPUT_VALIDATION,
            content={
                "video_path": video_path,
                "options": options or {}
            }
        )
        
        # Add to queue
        await self.data_queue.put(initial_data)
        
        # Start processing if not already running
        if self.pipeline_state == PipelineState.IDLE:
            asyncio.create_task(self._process_queue())
        
        self.logger.info(f"Added video to pipeline: {video_path} (ID: {data_id})")
        return data_id
    
    async def _process_queue(self):
        """Process items in the queue"""
        self.pipeline_state = PipelineState.RUNNING
        
        try:
            while self.pipeline_state == PipelineState.RUNNING:
                try:
                    # Get item from queue with timeout
                    data = await asyncio.wait_for(self.data_queue.get(), timeout=1.0)
                    
                    # Process data
                    task = asyncio.create_task(self._process_data(data))
                    self.active_processes[data.data_id] = task
                    
                    # Remove completed tasks
                    done, pending = await asyncio.wait(
                        [task for task in self.active_processes.values() if task.done()],
                        timeout=0.1
                    )
                    
                    for done_task in done:
                        # Find and remove completed task
                        for process_id, active_task in list(self.active_processes.items()):
                            if active_task == done_task:
                                del self.active_processes[process_id]
                                break
                
                except asyncio.TimeoutError:
                    # Queue is empty, check if we should stop
                    if self.data_queue.empty() and not self.active_processes:
                        self.pipeline_state = PipelineState.COMPLETED
                        self.logger.info("Pipeline processing completed")
                        break
                
                except Exception as e:
                    self.logger.error(f"Error processing queue: {e}")
        
        except Exception as e:
            self.pipeline_state = PipelineState.FAILED
            self.logger.error(f"Pipeline processing failed: {e}")
    
    async def _process_data(self, data: PipelineData):
        """Process data through pipeline stages"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing data: {data.data_id}")
            
            # Process through each stage
            for stage in [
                PipelineStage.INPUT_VALIDATION,
                PipelineStage.VIDEO_ANALYSIS,
                PipelineStage.SCENE_DETECTION
            ]:
                if stage not in self.stages:
                    self.logger.warning(f"Stage not available: {stage.value}")
                    continue
                
                processor = self.stages[stage]
                
                # Validate input
                if not processor.validate_input(data):
                    data.mark_error(f"Invalid input for stage {stage.value}")
                    break
                
                # Process stage
                stage_start = time.time()
                data = await processor.process(data)
                stage_time = time.time() - stage_start
                
                # Validate output
                if not processor.validate_output(data):
                    data.mark_error(f"Invalid output from stage {stage.value}")
                    break
                
                # Update stage metrics
                if stage not in self.stage_metrics:
                    self.stage_metrics[stage] = processor.get_metrics()
                else:
                    self.stage_metrics[stage] = processor.get_metrics()
                
                # Check for errors
                if not data.is_valid():
                    self.logger.error(f"Stage {stage.value} failed: {data.error_info}")
                    break
                
                self.logger.debug(f"Completed stage {stage.value} in {stage_time:.2f}s")
            
            # Update pipeline metrics
            total_time = time.time() - start_time
            self.pipeline_metrics.total_processing_time += total_time
            
            if data.is_valid():
                self.pipeline_metrics.stages_completed += 1
                self.pipeline_metrics.success_rate = (
                    self.pipeline_metrics.stages_completed / 
                    (self.pipeline_metrics.stages_completed + self.pipeline_metrics.stages_failed)
                )
            else:
                self.pipeline_metrics.stages_failed += 1
                self.pipeline_metrics.error_count += 1
            
            # Store completed data
            self.completed_data[data.data_id] = data
            
            # Emit completion event
            self._event_system.emit("pipeline_item_completed", {
                "data_id": data.data_id,
                "success": data.is_valid(),
                "processing_time": total_time,
                "final_stage": data.stage.value,
                "quality_score": data.quality_score
            })
            
            self.logger.info(f"Completed processing: {data.data_id} (Success: {data.is_valid()})")
        
        except Exception as e:
            self.logger.error(f"Error processing data {data.data_id}: {e}")
            data.mark_error(f"Processing failed: {str(e)}")
            self.completed_data[data.data_id] = data
    
    async def get_processing_result(self, data_id: str) -> Optional[PipelineData]:
        """Get processing result for a data ID"""
        return self.completed_data.get(data_id)
    
    async def cancel_processing(self, data_id: str) -> bool:
        """Cancel processing for a specific data ID"""
        if data_id in self.active_processes:
            task = self.active_processes[data_id]
            task.cancel()
            del self.active_processes[data_id]
            
            # Mark as cancelled
            if data_id in self.completed_data:
                self.completed_data[data_id].mark_error("Processing cancelled")
            
            self.logger.info(f"Cancelled processing: {data_id}")
            return True
        
        return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status"""
        return {
            "queue_size": self.data_queue.qsize(),
            "active_processes": len(self.active_processes),
            "completed_items": len(self.completed_data),
            "pipeline_state": self.pipeline_state.value
        }
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed pipeline metrics"""
        return {
            "pipeline_metrics": self.pipeline_metrics.__dict__,
            "stage_metrics": {stage.value: metrics for stage, metrics in self.stage_metrics.items()},
            "queue_metrics": self.get_queue_status(),
            "performance_summary": {
                "average_stage_time": self.pipeline_metrics.average_stage_time,
                "throughput_per_minute": self.pipeline_metrics.data_throughput * 60,
                "success_rate_percentage": self.pipeline_metrics.success_rate * 100,
                "error_rate_percentage": (self.pipeline_metrics.error_count / 
                                         max(1, self.pipeline_metrics.stages_completed + self.pipeline_metrics.stages_failed)) * 100
            }
        }
    
    async def process_batch(self, video_paths: List[str]) -> List[str]:
        """Process multiple videos in batch"""
        data_ids = []
        
        for video_path in video_paths:
            try:
                data_id = await self.process_video(video_path)
                data_ids.append(data_id)
            except Exception as e:
                self.logger.error(f"Error adding video to batch: {video_path} - {e}")
        
        return data_ids
    
    def add_custom_stage(self, stage: PipelineStage, processor: PipelineStageProcessor):
        """Add a custom pipeline stage"""
        self.stages[stage] = processor
        self.logger.info(f"Added custom stage: {stage.value}")
    
    def remove_stage(self, stage: PipelineStage):
        """Remove a pipeline stage"""
        if stage in self.stages:
            del self.stages[stage]
            self.logger.info(f"Removed stage: {stage.value}")
    
    def reconfigure_pipeline(self, new_config: PipelineConfig):
        """Reconfigure pipeline with new settings"""
        self.config = new_config
        self.logger.info("Pipeline reconfigured")
        
        # Update executor if needed
        if new_config.max_concurrent_stages != self._executor._max_workers:
            self._executor.shutdown(wait=True)
            self._executor = ThreadPoolExecutor(max_workers=new_config.max_concurrent_stages)
    
    async def export_pipeline_state(self, file_path: str):
        """Export pipeline state to file"""
        state_data = {
            "timestamp": time.time(),
            "pipeline_state": self.pipeline_state.value,
            "metrics": self.get_detailed_metrics(),
            "completed_data": {
                data_id: {
                    "stage": data.stage.value,
                    "quality_score": data.quality_score,
                    "processing_time": data.processing_time,
                    "error_info": data.error_info
                }
                for data_id, data in self.completed_data.items()
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Pipeline state exported to: {file_path}")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        if not self.completed_data:
            return {"total_processed": 0}
        
        total_processed = len(self.completed_data)
        successful_processed = len([d for d in self.completed_data.values() if d.is_valid()])
        failed_processed = total_processed - successful_processed
        
        # Calculate average processing time
        processing_times = [d.processing_time for d in self.completed_data.values()]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Calculate average quality score
        quality_scores = [d.quality_score for d in self.completed_data.values() if d.is_valid()]
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            "total_processed": total_processed,
            "successful_processed": successful_processed,
            "failed_processed": failed_processed,
            "success_rate": successful_processed / total_processed if total_processed > 0 else 0,
            "average_processing_time": avg_processing_time,
            "average_quality_score": avg_quality_score,
            "total_errors": self.pipeline_metrics.error_count,
            "total_warnings": self.pipeline_metrics.warning_count
        }