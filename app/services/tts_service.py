"""
Text-to-Speech (TTS) system for VideoEpicCreator

This module provides comprehensive TTS capabilities with multiple voice engines,
voice customization, and audio processing for commentary narration.
"""

import asyncio
import os
import tempfile
from typing import Dict, List, Optional, Tuple, Any, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import logging
from pathlib import Path

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

from ..core.base import BaseComponent, ComponentConfig, ComponentState
from ..config.settings import Settings
from ..ai.commentary_generator import CommentarySegment, CommentaryScript


class TTSEngine(Enum):
    """Supported TTS engines"""
    EDGE_TTS = "edge_tts"      # Microsoft Edge TTS
    PYTTSX3 = "pyttsx3"        # pyttsx3 (offline)
    AZURE = "azure"            # Azure Cognitive Services
    GOOGLE = "google"          # Google Cloud TTS
    AMAZON = "amazon"          # Amazon Polly


class VoiceEmotion(Enum):
    """Voice emotion types"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    CALM = "calm"
    SERIOUS = "serious"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    DRAMATIC = "dramatic"


class VoiceGender(Enum):
    """Voice gender types"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


@dataclass
class VoiceProfile:
    """Voice profile configuration"""
    name: str
    engine: TTSEngine
    voice_id: str
    language: str
    gender: VoiceGender
    age: Optional[str] = None
    description: str = ""
    emotion_support: List[VoiceEmotion] = field(default_factory=list)
    default_speed: float = 1.0
    default_pitch: float = 1.0
    default_volume: float = 1.0


@dataclass
class TTSOptions:
    """TTS generation options"""
    voice_profile: VoiceProfile
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    emotion: VoiceEmotion = VoiceEmotion.NEUTRAL
    output_format: str = "mp3"
    sample_rate: int = 22050
    channels: int = 1
    quality: str = "standard"  # "standard", "high", "premium"


@dataclass
class AudioSegment:
    """Audio segment with timing information"""
    start_time: float
    end_time: float
    audio_path: str
    text: str
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSAudio:
    """Complete TTS audio output"""
    segments: List[AudioSegment]
    total_duration: float
    output_path: str
    voice_profile: VoiceProfile
    generation_options: TTSOptions
    metadata: Dict[str, Any] = field(default_factory=dict)


class TTSManager(BaseComponent[Dict[str, Any]]):
    """Text-to-Speech management system"""
    
    def __init__(self, settings: Settings, config: Optional[ComponentConfig] = None):
        super().__init__("tts_manager", config)
        self.settings = settings
        self.voice_profiles: Dict[str, VoiceProfile] = {}
        self.engine_instances: Dict[TTSEngine, Any] = {}
        self._initialize_voice_profiles()
        self._initialize_engines()
        
    def _initialize_voice_profiles(self):
        """Initialize available voice profiles"""
        # Edge TTS voices
        if EDGE_TTS_AVAILABLE:
            self.voice_profiles.update({
                "edge-xiaoxiao": VoiceProfile(
                    name="晓晓",
                    engine=TTSEngine.EDGE_TTS,
                    voice_id="zh-CN-XiaoxiaoNeural",
                    language="zh-CN",
                    gender=VoiceGender.FEMALE,
                    age="young",
                    description="年轻女声，自然亲切",
                    emotion_support=[VoiceEmotion.NEUTRAL, VoiceEmotion.HAPPY, VoiceEmotion.CALM],
                    default_speed=1.0
                ),
                "edge-yunyang": VoiceProfile(
                    name="云扬",
                    engine=TTSEngine.EDGE_TTS,
                    voice_id="zh-CN-YunyangNeural",
                    language="zh-CN",
                    gender=VoiceGender.MALE,
                    age="adult",
                    description="成熟男声，稳重专业",
                    emotion_support=[VoiceEmotion.NEUTRAL, VoiceEmotion.SERIOUS, VoiceEmotion.PROFESSIONAL],
                    default_speed=1.0
                ),
                "edge-xiaoxuan": VoiceProfile(
                    name="晓萱",
                    engine=TTSEngine.EDGE_TTS,
                    voice_id="zh-CN-XiaoxuanNeural",
                    language="zh-CN",
                    gender=VoiceGender.FEMALE,
                    age="child",
                    description="儿童女声，活泼可爱",
                    emotion_support=[VoiceEmotion.HAPPY, VoiceEmotion.EXCITED, VoiceEmotion.FRIENDLY],
                    default_speed=1.0
                )
            })
        
        # pyttsx3 voices
        if PYTTSX3_AVAILABLE:
            self.voice_profiles.update({
                "pyttsx3-default": VoiceProfile(
                    name="默认语音",
                    engine=TTSEngine.PYTTSX3,
                    voice_id="default",
                    language="zh-CN",
                    gender=VoiceGender.NEUTRAL,
                    description="系统默认语音",
                    emotion_support=[VoiceEmotion.NEUTRAL],
                    default_speed=1.0
                )
            })
    
    def _initialize_engines(self):
        """Initialize TTS engine instances"""
        try:
            if PYTTSX3_AVAILABLE:
                self.engine_instances[TTSEngine.PYTTSX3] = pyttsx3.init()
        except Exception as e:
            self.logger.warning(f"Failed to initialize pyttsx3: {e}")
    
    async def initialize(self) -> bool:
        """Initialize TTS manager"""
        try:
            self.logger.info("Initializing TTS Manager")
            
            # Test available engines
            available_engines = await self._test_engines()
            self.logger.info(f"Available TTS engines: {available_engines}")
            
            self.set_state(ComponentState.RUNNING)
            return True
        
        except Exception as e:
            self.handle_error(e, "initialization")
            return False
    
    async def start(self) -> bool:
        """Start TTS manager"""
        self.set_state(ComponentState.RUNNING)
        return True
    
    async def stop(self) -> bool:
        """Stop TTS manager"""
        self.set_state(ComponentState.STOPPED)
        return True
    
    async def cleanup(self) -> bool:
        """Clean up resources"""
        for engine in self.engine_instances.values():
            try:
                if hasattr(engine, 'stop'):
                    engine.stop()
            except Exception:
                pass
        
        self.engine_instances.clear()
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get TTS manager status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "available_voices": len(self.voice_profiles),
            "available_engines": list(self.engine_instances.keys()),
            "metrics": self.metrics.__dict__
        }
    
    async def _test_engines(self) -> List[TTSEngine]:
        """Test which TTS engines are available"""
        available = []
        
        # Test Edge TTS
        if EDGE_TTS_AVAILABLE:
            try:
                voices = await edge_tts.list_voices()
                available.append(TTSEngine.EDGE_TTS)
            except Exception as e:
                self.logger.warning(f"Edge TTS not available: {e}")
        
        # Test pyttsx3
        if PYTTSX3_AVAILABLE and TTSEngine.PYTTSX3 in self.engine_instances:
            try:
                engine = self.engine_instances[TTSEngine.PYTTSX3]
                voices = engine.getProperty('voices')
                if voices:
                    available.append(TTSEngine.PYTTSX3)
            except Exception as e:
                self.logger.warning(f"pyttsx3 not available: {e}")
        
        return available
    
    def get_available_voices(self) -> List[VoiceProfile]:
        """Get list of available voice profiles"""
        return list(self.voice_profiles.values())
    
    def get_voice_profile(self, voice_name: str) -> Optional[VoiceProfile]:
        """Get voice profile by name"""
        return self.voice_profiles.get(voice_name)
    
    def get_voices_by_language(self, language: str) -> List[VoiceProfile]:
        """Get voice profiles by language"""
        return [voice for voice in self.voice_profiles.values() if voice.language == language]
    
    def get_voices_by_gender(self, gender: VoiceGender) -> List[VoiceProfile]:
        """Get voice profiles by gender"""
        return [voice for voice in self.voice_profiles.values() if voice.gender == gender]
    
    async def generate_speech(
        self,
        text: str,
        options: TTSOptions,
        output_path: Optional[str] = None
    ) -> str:
        """Generate speech from text"""
        try:
            if output_path is None:
                output_path = self._get_temp_output_path(options.output_format)
            
            # Route to appropriate engine
            if options.voice_profile.engine == TTSEngine.EDGE_TTS:
                await self._generate_with_edge_tts(text, options, output_path)
            elif options.voice_profile.engine == TTSEngine.PYTTSX3:
                await self._generate_with_pyttsx3(text, options, output_path)
            else:
                raise ValueError(f"Unsupported TTS engine: {options.voice_profile.engine}")
            
            self.logger.info(f"Generated speech: {output_path}")
            return output_path
        
        except Exception as e:
            self.handle_error(e, "generate_speech")
            raise
    
    async def _generate_with_edge_tts(self, text: str, options: TTSOptions, output_path: str):
        """Generate speech using Edge TTS"""
        try:
            # Configure voice parameters
            communicate = edge_tts.Communicate(
                text=text,
                voice=options.voice_profile.voice_id,
                rate=f"{options.speed:+.1f}%",
                volume=f"{options.volume:+.1f}%",
                pitch=f"{options.pitch:+.1f}Hz"
            )
            
            # Generate audio
            await communicate.save(output_path)
        
        except Exception as e:
            self.logger.error(f"Edge TTS generation failed: {e}")
            raise
    
    async def _generate_with_pyttsx3(self, text: str, options: TTSOptions, output_path: str):
        """Generate speech using pyttsx3"""
        try:
            engine = self.engine_instances[TTSEngine.PYTTSX3]
            
            # Configure engine
            engine.setProperty('rate', int(200 * options.speed))
            engine.setProperty('volume', options.volume)
            
            # Save to file
            engine.save_to_file(text, output_path)
            engine.runAndWait()
        
        except Exception as e:
            self.logger.error(f"pyttsx3 generation failed: {e}")
            raise
    
    async def generate_commentary_audio(
        self,
        script: CommentaryScript,
        voice_profile_name: str,
        options: Optional[TTSOptions] = None,
        progress_callback: Optional[callable] = None
    ) -> TTSAudio:
        """Generate complete commentary audio from script"""
        try:
            voice_profile = self.get_voice_profile(voice_profile_name)
            if not voice_profile:
                raise ValueError(f"Voice profile not found: {voice_profile_name}")
            
            if options is None:
                options = TTSOptions(voice_profile=voice_profile)
            else:
                options.voice_profile = voice_profile
            
            self.logger.info(f"Generating commentary audio with {voice_profile.name}")
            start_time = asyncio.get_event_loop().time()
            
            # Create output directory
            with tempfile.TemporaryDirectory() as temp_dir:
                audio_segments = []
                total_duration = 0.0
                
                # Generate audio for each segment
                for i, segment in enumerate(script.segments):
                    if progress_callback:
                        progress_callback(i / len(script.segments), f"生成片段{i+1}音频...")
                    
                    # Adjust TTS options based on segment emotion
                    segment_options = self._adjust_options_for_emotion(options, segment)
                    
                    # Generate audio
                    segment_output = os.path.join(temp_dir, f"segment_{i:03d}.{options.output_format}")
                    audio_path = await self.generate_speech(segment.content, segment_options, segment_output)
                    
                    # Get audio duration
                    duration = await self._get_audio_duration(audio_path)
                    
                    # Create audio segment
                    audio_segment = AudioSegment(
                        start_time=segment.start_time,
                        end_time=segment.end_time,
                        audio_path=audio_path,
                        text=segment.content,
                        duration=duration,
                        metadata={
                            "segment_index": i,
                            "emotion": segment.emotion.value,
                            "importance": segment.importance,
                            "voice_profile": voice_profile.name
                        }
                    )
                    
                    audio_segments.append(audio_segment)
                    total_duration += duration
                
                # Merge all audio segments
                final_output = self._get_temp_output_path(options.output_format)
                await self._merge_audio_segments(audio_segments, final_output)
                
                # Create TTSAudio object
                tts_audio = TTSAudio(
                    segments=audio_segments,
                    total_duration=total_duration,
                    output_path=final_output,
                    voice_profile=voice_profile,
                    generation_options=options,
                    metadata={
                        "generation_time": start_time,
                        "script_title": script.title,
                        "total_segments": len(script.segments),
                        "engine": voice_profile.engine.value
                    }
                )
                
                # Update metrics
                processing_time = asyncio.get_event_loop().time() - start_time
                self.update_metrics(processing_time)
                
                if progress_callback:
                    progress_callback(1.0, "音频生成完成")
                
                self.logger.info(f"Commentary audio generated in {processing_time:.2f}s")
                return tts_audio
        
        except Exception as e:
            self.handle_error(e, "generate_commentary_audio")
            raise
    
    def _adjust_options_for_emotion(self, options: TTSOptions, segment: CommentarySegment) -> TTSOptions:
        """Adjust TTS options based on segment emotion"""
        # Create a copy of options
        adjusted_options = TTSOptions(
            voice_profile=options.voice_profile,
            speed=options.speed,
            pitch=options.pitch,
            volume=options.volume,
            emotion=options.emotion,
            output_format=options.output_format,
            sample_rate=options.sample_rate,
            channels=options.channels,
            quality=options.quality
        )
        
        # Adjust parameters based on emotion
        emotion_map = {
            "excited": {"speed": 1.2, "pitch": 1.1, "volume": 1.1},
            "sad": {"speed": 0.8, "pitch": 0.9, "volume": 0.9},
            "angry": {"speed": 1.1, "pitch": 1.2, "volume": 1.2},
            "calm": {"speed": 0.9, "pitch": 1.0, "volume": 0.9},
            "happy": {"speed": 1.1, "pitch": 1.1, "volume": 1.0},
            "serious": {"speed": 0.9, "pitch": 0.9, "volume": 1.0},
            "dramatic": {"speed": 1.0, "pitch": 1.2, "volume": 1.1}
        }
        
        emotion_key = segment.emotion.value.lower()
        if emotion_key in emotion_map:
            adjustments = emotion_map[emotion_key]
            adjusted_options.speed *= adjustments["speed"]
            adjusted_options.pitch *= adjustments["pitch"]
            adjusted_options.volume *= adjustments["volume"]
        
        # Apply delivery hints
        if segment.delivery_hints:
            if "pace" in segment.delivery_hints:
                pace = segment.delivery_hints["pace"]
                if pace == "fast":
                    adjusted_options.speed *= 1.2
                elif pace == "slow":
                    adjusted_options.speed *= 0.8
            
            if "emphasis" in segment.delivery_hints:
                emphasis = segment.delivery_hints["emphasis"]
                if emphasis == "high":
                    adjusted_options.volume *= 1.1
                    adjusted_options.pitch *= 1.1
        
        return adjusted_options
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration from file"""
        try:
            # This is a simplified implementation
            # In a full implementation, you would use a proper audio library
            import subprocess
            result = subprocess.run(
                ["ffprobe", "-i", audio_path, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except Exception:
            # Fallback estimation
            return 0.0
    
    async def _merge_audio_segments(self, segments: List[AudioSegment], output_path: str):
        """Merge multiple audio segments into one file"""
        try:
            # Create concat file
            concat_file = output_path + ".concat.txt"
            with open(concat_file, 'w') as f:
                for segment in segments:
                    f.write(f"file '{segment.audio_path}'\n")
            
            # Merge using ffmpeg
            import subprocess
            subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file,
                "-c", "copy", output_path
            ], check=True, capture_output=True)
            
            # Clean up concat file
            os.unlink(concat_file)
        
        except Exception as e:
            self.logger.error(f"Audio merging failed: {e}")
            raise
    
    def _get_temp_output_path(self, format: str) -> str:
        """Get temporary output file path"""
        import tempfile
        import uuid
        
        temp_dir = tempfile.gettempdir()
        filename = f"tts_{uuid.uuid4().hex[:8]}.{format}"
        return os.path.join(temp_dir, filename)
    
    async def preview_voice(
        self,
        voice_profile_name: str,
        sample_text: str = "这是一个语音预览示例。"
    ) -> str:
        """Generate a preview of a voice"""
        try:
            voice_profile = self.get_voice_profile(voice_profile_name)
            if not voice_profile:
                raise ValueError(f"Voice profile not found: {voice_profile_name}")
            
            options = TTSOptions(voice_profile=voice_profile)
            preview_path = self._get_temp_output_path("mp3")
            
            await self.generate_speech(sample_text, options, preview_path)
            return preview_path
        
        except Exception as e:
            self.handle_error(e, "preview_voice")
            raise
    
    async def batch_generate_speech(
        self,
        texts: List[str],
        options: TTSOptions,
        output_dir: str,
        progress_callback: Optional[callable] = None
    ) -> List[str]:
        """Generate speech for multiple texts"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            output_paths = []
            
            for i, text in enumerate(texts):
                if progress_callback:
                    progress_callback(i / len(texts), f"生成第{i+1}个音频...")
                
                output_path = os.path.join(output_dir, f"speech_{i:03d}.{options.output_format}")
                await self.generate_speech(text, options, output_path)
                output_paths.append(output_path)
            
            return output_paths
        
        except Exception as e:
            self.handle_error(e, "batch_generate_speech")
            raise
    
    async def optimize_audio(
        self,
        audio_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> str:
        """Optimize audio quality"""
        try:
            # Apply audio processing using ffmpeg
            import subprocess
            
            cmd = ["ffmpeg", "-i", audio_path]
            
            # Apply normalization
            if options.get("normalize", False):
                cmd.extend(["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"])
            
            # Apply noise reduction
            if options.get("denoise", False):
                cmd.extend(["-af", "afftdn=nf=-25"])
            
            # Apply compression
            if options.get("compress", False):
                cmd.extend(["-af", "acompressor"])
            
            # Set quality
            cmd.extend(["-q:a", str(options.get("quality", 2))])
            
            cmd.extend(["-y", output_path])
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            return output_path
        
        except Exception as e:
            self.handle_error(e, "optimize_audio")
            raise
    
    def get_voice_recommendations(
        self,
        script: CommentaryScript,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[VoiceProfile]:
        """Get recommended voice profiles for a script"""
        try:
            recommendations = []
            
            # Analyze script characteristics
            emotions = [segment.emotion for segment in script.segments]
            dominant_emotion = max(set(emotions), key=emotions.count) if emotions else VoiceEmotion.NEUTRAL
            
            # Get voices that support the dominant emotion
            suitable_voices = [
                voice for voice in self.voice_profiles.values()
                if dominant_emotion in voice.emotion_support or VoiceEmotion.NEUTRAL in voice.emotion_support
            ]
            
            # Sort by relevance
            for voice in suitable_voices:
                score = 0
                
                # Gender preference
                if user_preferences and "gender" in user_preferences:
                    if voice.gender == user_preferences["gender"]:
                        score += 2
                
                # Age preference
                if user_preferences and "age" in user_preferences:
                    if voice.age == user_preferences["age"]:
                        score += 1
                
                # Engine preference
                if user_preferences and "engine" in user_preferences:
                    if voice.engine == user_preferences["engine"]:
                        score += 1
                
                # Emotion support
                if dominant_emotion in voice.emotion_support:
                    score += 2
                
                recommendations.append((voice, score))
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x[1], reverse=True)
            return [voice for voice, score in recommendations[:5]]
        
        except Exception as e:
            self.handle_error(e, "get_voice_recommendations")
            return list(self.voice_profiles.values())[:3]
    
    def export_audio_metadata(self, tts_audio: TTSAudio, output_path: str):
        """Export audio metadata to JSON file"""
        try:
            metadata = {
                "title": tts_audio.metadata.get("script_title", "Untitled"),
                "voice_profile": tts_audio.voice_profile.name,
                "total_duration": tts_audio.total_duration,
                "segments": [
                    {
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "text": seg.text,
                        "duration": seg.duration,
                        "metadata": seg.metadata
                    }
                    for seg in tts_audio.segments
                ],
                "generation_options": {
                    "speed": tts_audio.generation_options.speed,
                    "pitch": tts_audio.generation_options.pitch,
                    "volume": tts_audio.generation_options.volume,
                    "emotion": tts_audio.generation_options.emotion.value,
                    "quality": tts_audio.generation_options.quality
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Audio metadata exported to {output_path}")
        
        except Exception as e:
            self.handle_error(e, "export_audio_metadata")
            raise


# Fix the missing import
import uuid