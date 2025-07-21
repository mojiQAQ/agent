import base64
import json
import time
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tts.v20190823 import tts_client, models
from modules.config import get_tencent_config
from modules.logger import get_logger
from pathlib import Path

class AudioGenerator:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.tencent_config = get_tencent_config()
        self.output_dir = Path("output")
        
        # 初始化腾讯云客户端
        cred = credential.Credential(
            self.tencent_config['secret_id'], 
            self.tencent_config['secret_key']
        )
        http_profile = HttpProfile()
        http_profile.endpoint = "tts.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        self.client = tts_client.TtsClient(
            cred, 
            self.tencent_config.get('region', 'ap-guangzhou'), 
            client_profile
        )

    def generate(self, text: str, type: str = "word", language: str = "en", output_path: str = None) -> str:
        """
        使用腾讯云API生成语音
        
        Args:
            text: 要转换为语音的文本
            type: 文本类型，默认为 word, 可选值为 word, phrase
            language: 语言，默认为英文 (en)，可选值为中文 (zh)
            output_path: 输出路径，默认为None
            
        Returns:
            str: 生成的音频文件路径
        """
        try:
            self.logger.info(f"开始生成语音: {text}")
            # 创建请求对象
            req = models.TextToVoiceRequest()
            
            # 根据语言选择不同的参数
            if language == "zh":
                primary_language = 1  # 中文
                voice_type = self.tencent_config['voice_zh']   # 中文女声 (爱小璟)
            else:
                primary_language = 2  # 英文
                voice_type = self.tencent_config['voice_en']   # 英文女声 (WeWinny)
            
            params = {
                "Text": text,
                "SessionId": f"session-{int(time.time())}",
                "ModelType": 1,           # 1: 标准音色
                "Volume": 5,              # 音量大小
                "Speed": 0.8,               # 语速
                "SampleRate": 16000,      # 采样率
                "Codec": "wav",           # 音频格式
                "PrimaryLanguage": primary_language,
                "VoiceType": voice_type,
            }
            req.from_json_string(json.dumps(params))
            
            # 发送请求
            self.logger.debug("发送语音合成请求到腾讯云")
            resp = self.client.TextToVoice(req)
            
            # 确定输出路径
            if not output_path:
                timestamp = int(time.time())
                output_path = self.output_dir / f"{timestamp}_{type}_{language}.wav"
            else:
                output_path = Path(output_path)
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存音频文件
            decoded_audio_data = base64.b64decode(resp.Audio)
            with open(str(output_path), 'wb') as f:
                f.write(decoded_audio_data)
            
            self.logger.info(f"语音文件已保存: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"生成语音时出错: {str(e)}")
            raise Exception(f"Error generating audio: {str(e)}") 