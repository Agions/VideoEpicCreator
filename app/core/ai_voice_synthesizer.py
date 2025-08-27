#!/usr/bin/env python3
"""
AI语音合成器
提供高质量的文本转语音服务，支持多种语音风格和情感
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union, BinaryIO
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import tempfile
import os
import wave
import struct
import numpy as np

# 语音合成服务提供商
try:
    import openai
    from openai import AsyncOpenAI
except ImportError:
    openai = None
    AsyncOpenAI = None

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None

try:
    from google.cloud import texttospeech
except ImportError:
    texttospeech = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

from ..utils.config import Config
from ..utils.file_utils import FileUtils

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoiceProvider(Enum):
    """语音合成提供商枚举"""
    OPENAI = "openai"
    AZURE = "azure"
    GOOGLE = "google"
    LOCAL = "local"

class VoiceStyle(Enum):
    """语音风格枚举"""
    NEUTRAL = "neutral"          # 中性
    CHEERFUL = "cheerful"        # 愉快
    SERIOUS = "serious"          # 严肃
    FRIENDLY = "friendly"        # 友好
    PROFESSIONAL = "professional" # 专业
    EMPATHETIC = "empathetic"    # 共情
    CALM = "calm"                # 平静
    EXCITED = "excited"          # 兴奋

class VoiceGender(Enum):
    """语音性别枚举"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

class AudioFormat(Enum):
    """音频格式枚举"""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"

@dataclass
class VoiceProfile:
    """语音配置文件"""
    voice_id: str
    name: str
    provider: VoiceProvider
    gender: VoiceGender
    language: str
    style: VoiceStyle
    pitch: float = 1.0
    speed: float = 1.0
    volume: float = 1.0
    description: str = ""

@dataclass
class SynthesisRequest:
    """合成请求"""
    request_id: str
    text: str
    voice_profile: VoiceProfile
    audio_format: AudioFormat
    output_path: Optional[str] = None
    ssml_instructions: Optional[str] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}

@dataclass
class SynthesisResult:
    """合成结果"""
    request_id: str
    success: bool
    audio_data: bytes = b""
    output_path: str = ""
    duration: float = 0
    metadata: Dict[str, Any] = None
    error: str = ""
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class AIVoiceSynthesizer:
    """AI语音合成器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.file_utils = FileUtils()
        
        # 初始化语音合成客户端
        self.clients = {}
        self._init_voice_clients()
        
        # 语音配置文件
        self.voice_profiles = self._load_voice_profiles()
        
        # 合成队列
        self.synthesis_queue = asyncio.Queue()
        self.active_synthesis = {}
        self.completed_synthesis = {}
        
        # 合成统计
        self.synthesis_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_duration': 0,
            'provider_stats': {}
        }
        
        # 启动处理器
        self._running = False
        self.processor_task = None
    
    def _init_voice_clients(self):
        """初始化语音合成客户端"""
        try:
            # OpenAI TTS
            if openai and self.config.get('openai_api_key'):
                self.clients[VoiceProvider.OPENAI] = AsyncOpenAI(
                    api_key=self.config.get('openai_api_key')
                )
                logger.info("OpenAI TTS客户端初始化成功")
        except Exception as e:
            logger.warning(f"OpenAI TTS客户端初始化失败: {e}")
        
        try:
            # Azure Speech Service
            if speechsdk and self.config.get('azure_speech_key'):
                speech_config = speechsdk.SpeechConfig(
                    subscription=self.config.get('azure_speech_key'),
                    region=self.config.get('azure_speech_region', 'eastus')
                )
                self.clients[VoiceProvider.AZURE] = speech_config
                logger.info("Azure Speech Service客户端初始化成功")
        except Exception as e:
            logger.warning(f"Azure Speech Service客户端初始化失败: {e}")
        
        try:
            # Google Text-to-Speech
            if texttospeech and self.config.get('google_tts_key'):
                client = texttospeech.TextToSpeechClient()
                self.clients[VoiceProvider.GOOGLE] = client
                logger.info("Google Text-to-Speech客户端初始化成功")
        except Exception as e:
            logger.warning(f"Google Text-to-Speech客户端初始化失败: {e}")
        
        try:
            # 本地TTS (pyttsx3)
            if pyttsx3:
                self.clients[VoiceProvider.LOCAL] = pyttsx3.init()
                logger.info("本地TTS客户端初始化成功")
        except Exception as e:
            logger.warning(f"本地TTS客户端初始化失败: {e}")
    
    def _load_voice_profiles(self) -> Dict[str, VoiceProfile]:
        """加载语音配置文件"""
        profiles = {}
        
        # OpenAI语音
        if VoiceProvider.OPENAI in self.clients:
            profiles.update({
                'openai_alloy': VoiceProfile(
                    voice_id='alloy',
                    name='Alloy',
                    provider=VoiceProvider.OPENAI,
                    gender=VoiceGender.MALE,
                    language='en-US',
                    style=VoiceStyle.NEUTRAL,
                    description='OpenAI默认男声'
                ),
                'openai_echo': VoiceProfile(
                    voice_id='echo',
                    name='Echo',
                    provider=VoiceProvider.OPENAI,
                    gender=VoiceGender.MALE,
                    language='en-US',
                    style=VoiceStyle.FRIENDLY,
                    description='OpenAI友好男声'
                ),
                'openai_fable': VoiceProfile(
                    voice_id='fable',
                    name='Fable',
                    provider=VoiceProvider.OPENAI,
                    gender=VoiceGender.MALE,
                    language='en-US',
                    style=VoiceStyle.EMPATHETIC,
                    description='OpenAI共情男声'
                ),
                'openai_onyx': VoiceProfile(
                    voice_id='onyx',
                    name='Onyx',
                    provider=VoiceProvider.OPENAI,
                    gender=VoiceGender.MALE,
                    language='en-US',
                    style=VoiceStyle.SERIOUS,
                    description='OpenAI严肃男声'
                ),
                'openai_nova': VoiceProfile(
                    voice_id='nova',
                    name='Nova',
                    provider=VoiceProvider.OPENAI,
                    gender=VoiceGender.FEMALE,
                    language='en-US',
                    style=VoiceStyle.FRIENDLY,
                    description='OpenAI友好女声'
                ),
                'openai_shimmer': VoiceProfile(
                    voice_id='shimmer',
                    name='Shimmer',
                    provider=VoiceProvider.OPENAI,
                    gender=VoiceGender.FEMALE,
                    language='en-US',
                    style=VoiceStyle.CHEERFUL,
                    description='OpenAI愉快女声'
                )
            })
        
        # 本地语音
        if VoiceProvider.LOCAL in self.clients:
            profiles.update({
                'local_default': VoiceProfile(
                    voice_id='default',
                    name='默认语音',
                    provider=VoiceProvider.LOCAL,
                    gender=VoiceGender.NEUTRAL,
                    language='zh-CN',
                    style=VoiceStyle.NEUTRAL,
                    description='系统默认语音'
                )
            })
        
        return profiles
    
    async def start(self):
        """启动语音合成器"""
        if self._running:
            return
        
        self._running = True
        self.processor_task = asyncio.create_task(self._process_synthesis_requests())
        logger.info("AI语音合成器已启动")
    
    async def stop(self):
        """停止语音合成器"""
        if not self._running:
            return
        
        self._running = False
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("AI语音合成器已停止")
    
    async def synthesize_speech(self, request: SynthesisRequest) -> str:
        """合成语音"""
        try:
            # 验证请求
            if not self._validate_synthesis_request(request):
                raise ValueError("无效的语音合成请求")
            
            # 更新统计
            self.synthesis_stats['total_requests'] += 1
            
            # 将请求加入队列
            await self.synthesis_queue.put(request)
            self.active_synthesis[request.request_id] = request
            
            logger.info(f"语音合成请求已加入队列: {request.request_id}")
            return request.request_id
            
        except Exception as e:
            logger.error(f"合成语音时出错: {e}")
            raise
    
    async def get_synthesis_status(self, request_id: str) -> Optional[SynthesisResult]:
        """获取合成状态"""
        # 检查活跃请求
        if request_id in self.active_synthesis:
            return SynthesisResult(
                request_id=request_id,
                success=False,
                error="正在处理中"
            )
        
        # 检查已完成请求
        if request_id in self.completed_synthesis:
            return self.completed_synthesis[request_id]
        
        return None
    
    async def _process_synthesis_requests(self):
        """处理语音合成请求"""
        while self._running:
            try:
                # 从队列获取请求
                request = await asyncio.wait_for(self.synthesis_queue.get(), timeout=1.0)
                
                # 处理请求
                asyncio.create_task(self._handle_synthesis_request(request))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"处理语音合成请求时出错: {e}")
    
    async def _handle_synthesis_request(self, request: SynthesisRequest):
        """处理单个语音合成请求"""
        try:
            # 创建结果对象
            result = SynthesisResult(
                request_id=request.request_id,
                success=False
            )
            
            # 根据提供商调用相应的合成方法
            if request.voice_profile.provider == VoiceProvider.OPENAI:
                audio_data = await self._synthesize_with_openai(request)
            elif request.voice_profile.provider == VoiceProvider.AZURE:
                audio_data = await self._synthesize_with_azure(request)
            elif request.voice_profile.provider == VoiceProvider.GOOGLE:
                audio_data = await self._synthesize_with_google(request)
            elif request.voice_profile.provider == VoiceProvider.LOCAL:
                audio_data = await self._synthesize_with_local(request)
            else:
                raise ValueError(f"不支持的语音合成提供商: {request.voice_profile.provider}")
            
            if audio_data:
                # 保存音频文件
                output_path = await self._save_audio_file(audio_data, request)
                
                # 计算音频时长
                duration = self._calculate_audio_duration(audio_data)
                
                # 更新结果
                result.success = True
                result.audio_data = audio_data
                result.output_path = output_path
                result.duration = duration
                
                # 更新统计
                self.synthesis_stats['successful_requests'] += 1
                self.synthesis_stats['total_duration'] += duration
                self._update_provider_stats(request.voice_profile.provider, True, duration)
                
                logger.info(f"语音合成完成: {request.request_id}, 时长: {duration:.2f}秒")
            else:
                result.error = "语音合成失败"
                self.synthesis_stats['failed_requests'] += 1
                self._update_provider_stats(request.voice_profile.provider, False, 0)
                
        except Exception as e:
            # 更新结果为失败
            result.success = False
            result.error = str(e)
            self.synthesis_stats['failed_requests'] += 1
            self._update_provider_stats(request.voice_profile.provider, False, 0)
            
            logger.error(f"语音合成失败: {request.request_id}, 错误: {e}")
        
        finally:
            # 从活跃请求中移除
            self.active_synthesis.pop(request.request_id, None)
            
            # 添加到已完成请求
            self.completed_synthesis[request.request_id] = result
            
            # 清理旧请求（保留最近500个）
            if len(self.completed_synthesis) > 500:
                oldest_keys = sorted(self.completed_synthesis.keys())[:100]
                for key in oldest_keys:
                    self.completed_synthesis.pop(key, None)
    
    async def _synthesize_with_openai(self, request: SynthesisRequest) -> Optional[bytes]:
        """使用OpenAI合成语音"""
        if VoiceProvider.OPENAI not in self.clients:
            raise ValueError("OpenAI TTS客户端未初始化")
        
        client = self.clients[VoiceProvider.OPENAI]
        
        # 构建SSML（如果提供了指令）
        if request.ssml_instructions:
            text = request.ssml_instructions
        else:
            text = request.text
        
        try:
            # 调用OpenAI TTS API
            response = await client.audio.speech.create(
                model="tts-1",
                voice=request.voice_profile.voice_id,
                input=text,
                speed=request.voice_profile.speed
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"OpenAI TTS合成失败: {e}")
            return None
    
    async def _synthesize_with_azure(self, request: SynthesisRequest) -> Optional[bytes]:
        """使用Azure合成语音"""
        if VoiceProvider.AZURE not in self.clients:
            raise ValueError("Azure Speech Service客户端未初始化")
        
        # Azure语音合成需要同步调用，使用线程池
        def _azure_synthesis():
            try:
                speech_config = self.clients[VoiceProvider.AZURE]
                
                # 设置语音
                speech_config.speech_synthesis_voice_name = request.voice_profile.voice_id
                
                # 设置语音参数
                speech_config.speech_synthesis_prosody = speechsdk.SpeechSynthesisProsody(
                    rate=str(request.voice_profile.speed),
                    pitch=str(request.voice_profile.pitch),
                    volume=str(request.voice_profile.volume)
                )
                
                # 创建合成器
                synthesizer = speechsdk.SpeechSynthesizer(speech_config)
                
                # 合成语音
                result = synthesizer.speak_text_async(request.text).get()
                
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    return result.audio_data
                else:
                    logger.error(f"Azure语音合成失败: {result.reason}")
                    return None
                    
            except Exception as e:
                logger.error(f"Azure语音合成出错: {e}")
                return None
        
        # 在线程池中执行
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _azure_synthesis)
    
    async def _synthesize_with_google(self, request: SynthesisRequest) -> Optional[bytes]:
        """使用Google合成语音"""
        if VoiceProvider.GOOGLE not in self.clients:
            raise ValueError("Google Text-to-Speech客户端未初始化")
        
        client = self.clients[VoiceProvider.GOOGLE]
        
        try:
            # 构建合成请求
            synthesis_input = texttospeech.SynthesisInput(text=request.text)
            
            # 构建语音配置
            voice = texttospeech.VoiceSelectionParams(
                language_code=request.voice_profile.language,
                name=request.voice_profile.voice_id,
                ssml_gender=texttospeech.SsmlVoiceGender[request.voice_profile.gender.value.upper()]
            )
            
            # 构建音频配置
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding[request.audio_format.value.upper()]
            )
            
            # 合成语音
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            return response.audio_content
            
        except Exception as e:
            logger.error(f"Google TTS合成失败: {e}")
            return None
    
    async def _synthesize_with_local(self, request: SynthesisRequest) -> Optional[bytes]:
        """使用本地TTS合成语音"""
        if VoiceProvider.LOCAL not in self.clients:
            raise ValueError("本地TTS客户端未初始化")
        
        # 本地TTS需要同步调用，使用线程池
        def _local_synthesis():
            try:
                engine = self.clients[VoiceProvider.LOCAL]
                
                # 创建临时文件
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                # 设置语音属性
                engine.setProperty('rate', int(request.voice_profile.speed * 200))
                engine.setProperty('volume', request.voice_profile.volume)
                
                # 保存到文件
                engine.save_to_file(request.text, temp_path)
                engine.runAndWait()
                
                # 读取音频数据
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
                # 清理临时文件
                os.unlink(temp_path)
                
                return audio_data
                
            except Exception as e:
                logger.error(f"本地TTS合成出错: {e}")
                return None
        
        # 在线程池中执行
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _local_synthesis)
    
    async def _save_audio_file(self, audio_data: bytes, request: SynthesisRequest) -> str:
        """保存音频文件"""
        if request.output_path:
            output_path = Path(request.output_path)
        else:
            # 生成默认输出路径
            output_dir = Path(self.config.get('audio_output_dir', 'output/audio'))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = output_dir / f"{request.request_id}.{request.audio_format.value}"
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        with open(output_path, 'wb') as f:
            f.write(audio_data)
        
        return str(output_path)
    
    def _calculate_audio_duration(self, audio_data: bytes) -> float:
        """计算音频时长"""
        try:
            # 简单的WAV文件时长计算
            if len(audio_data) < 44:  # WAV文件头最小大小
                return 0.0
            
            # 解析WAV文件头
            riff_header = audio_data[:4]
            if riff_header != b'RIFF':
                # 不是WAV格式，使用估算
                return len(audio_data) / 16000.0  # 假设16kHz采样率
            
            # 获取采样率
            sample_rate = struct.unpack('<I', audio_data[24:28])[0]
            channels = struct.unpack('<H', audio_data[22:24])[0]
            bits_per_sample = struct.unpack('<H', audio_data[34:36])[0]
            
            # 计算数据大小
            data_size = len(audio_data) - 44
            
            # 计算时长
            duration = data_size / (sample_rate * channels * bits_per_sample / 8)
            
            return duration
            
        except Exception as e:
            logger.error(f"计算音频时长时出错: {e}")
            return 0.0
    
    def _validate_synthesis_request(self, request: SynthesisRequest) -> bool:
        """验证语音合成请求"""
        if not request.request_id:
            return False
        
        if not request.text.strip():
            return False
        
        if request.voice_profile.provider not in self.clients:
            return False
        
        if not request.voice_profile.voice_id:
            return False
        
        return True
    
    def _update_provider_stats(self, provider: VoiceProvider, success: bool, duration: float):
        """更新提供商统计"""
        if provider.value not in self.synthesis_stats['provider_stats']:
            self.synthesis_stats['provider_stats'][provider.value] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'total_duration': 0
            }
        
        stats = self.synthesis_stats['provider_stats'][provider.value]
        stats['total_requests'] += 1
        
        if success:
            stats['successful_requests'] += 1
            stats['total_duration'] += duration
        else:
            stats['failed_requests'] += 1
    
    def get_available_providers(self) -> List[VoiceProvider]:
        """获取可用的语音合成提供商"""
        return list(self.clients.keys())
    
    def get_voice_profiles(self, provider: Optional[VoiceProvider] = None) -> List[VoiceProfile]:
        """获取语音配置文件"""
        if provider:
            return [profile for profile in self.voice_profiles.values() 
                   if profile.provider == provider]
        else:
            return list(self.voice_profiles.values())
    
    def get_synthesis_stats(self) -> Dict[str, Any]:
        """获取合成统计"""
        return self.synthesis_stats.copy()
    
    def create_ssml(self, text: str, voice_profile: VoiceProfile, 
                   prosody: Dict[str, float] = None) -> str:
        """创建SSML标记"""
        if prosody is None:
            prosody = {}
        
        pitch = prosody.get('pitch', voice_profile.pitch)
        rate = prosody.get('rate', voice_profile.speed)
        volume = prosody.get('volume', voice_profile.volume)
        
        ssml = f"""
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{voice_profile.language}">
    <voice name="{voice_profile.voice_id}">
        <prosody pitch="{pitch}%" rate="{rate}%" volume="{volume}%">
            {text}
        </prosody>
    </voice>
</speak>
"""
        
        return ssml.strip()
    
    def estimate_audio_duration(self, text: str, speaking_rate: int = 150) -> float:
        """估算音频时长"""
        # 移除标点符号和多余空格
        clean_text = re.sub(r'[^\w\s]', '', text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # 计算字数
        word_count = len(clean_text.split())
        
        # 估算时长（秒）
        return word_count / (speaking_rate / 60)

def main():
    """主函数"""
    # 测试语音合成器
    from app.utils.config import Config
    
    # 创建配置
    config = Config()
    
    # 创建语音合成器
    synthesizer = AIVoiceSynthesizer(config)
    
    # 启动合成器
    asyncio.run(synthesizer.start())
    
    try:
        # 获取可用的语音配置
        profiles = synthesizer.get_voice_profiles()
        if profiles:
            voice_profile = profiles[0]
            print(f"使用语音: {voice_profile.name}")
        else:
            print("没有可用的语音配置")
            return
        
        # 创建合成请求
        request = SynthesisRequest(
            request_id="test_001",
            text="这是一个测试语音合成的示例文本。AI语音合成技术正在快速发展，为各种应用场景提供了高质量的语音解决方案。",
            voice_profile=voice_profile,
            audio_format=AudioFormat.WAV,
            context={
                'purpose': 'test',
                'language': 'zh-CN'
            }
        )
        
        print(f"开始语音合成: {request.request_id}")
        
        # 提交合成请求
        request_id = asyncio.run(synthesizer.synthesize_speech(request))
        print(f"请求已提交，ID: {request_id}")
        
        # 等待合成完成
        import time
        time.sleep(10)
        
        # 获取结果
        result = asyncio.run(synthesizer.get_synthesis_status(request_id))
        if result:
            print(f"合成状态: {'成功' if result.success else '失败'}")
            if result.success:
                print(f"输出路径: {result.output_path}")
                print(f"音频时长: {result.duration:.2f}秒")
                print(f"音频大小: {len(result.audio_data)} 字节")
            else:
                print(f"错误信息: {result.error}")
        else:
            print("未找到合成结果")
        
        # 显示统计信息
        stats = synthesizer.get_synthesis_stats()
        print(f"合成统计: {stats}")
        
    finally:
        # 停止合成器
        asyncio.run(synthesizer.stop())

if __name__ == "__main__":
    main()