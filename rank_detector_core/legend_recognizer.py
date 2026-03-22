import base64
import json
import io
import asyncio
import aiohttp
import requests
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from PIL import Image
import numpy as np
import cv2
from dataclasses import dataclass
from pathlib import Path


LEGENDARY_PROMPT = """你是一位游戏段位徽章识别专家，请识别这张图片是否是传奇(Legendary)段位。

【传奇(Legendary)特征】
- 红金火焰特效
- 顶部有红色/深红色水晶
- 金色边框装饰
- 底部有火焰/光芒纹理
- 下方有阿拉伯数字排名（如 58, 139, 5286, 9425, 13141 等）

如果不是传奇，返回 rank=Unknown, level=0
如果是传奇，返回 rank=Legendary, level=下方的排名数字

请以JSON格式返回：{"rank":"Legendary","level":58,"confidence":0.95}

只返回JSON，不要其他内容。"""

CROP_REGION = {"x1": 0.00, "y1": 0.00, "x2": 0.10, "y2": 0.25}


@dataclass
class RecognitionResult:
    rank: str           # "Legendary" 或 "Unknown"
    level: int          # 传奇排名，或 0
    confidence: float   # 置信度 0-1


# ==================== API策略抽象层 ====================

class APIStrategy(ABC):
    """API调用策略基类"""

    @abstractmethod
    def call(self, image_base64: str, prompt: str) -> dict:
        """同步调用API"""
        pass

    @abstractmethod
    async def acall(self, image_base64: str, prompt: str) -> dict:
        """异步调用API"""
        pass

    @abstractmethod
    def parse_response(self, response: dict) -> RecognitionResult:
        """解析API响应"""
        pass


class DoubaoStrategy(APIStrategy):
    """豆包/火山引擎 API策略"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def call(self, image_base64: str, prompt: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": [{
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": f"data:image/png;base64,{image_base64}"},
                    {"type": "input_text", "text": prompt}
                ]
            }]
        }
        response = requests.post(
            f"{self.base_url}/responses",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    async def acall(self, image_base64: str, prompt: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": [{
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": f"data:image/png;base64,{image_base64}"},
                    {"type": "input_text", "text": prompt}
                ]
            }]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/responses",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                response.raise_for_status()
                return await response.json()

    def parse_response(self, response: dict) -> RecognitionResult:
        try:
            content = ""
            for item in response.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            content = c.get("text", "")
                            break
            return self._extract_result(content)
        except (KeyError, IndexError, json.JSONDecodeError):
            return RecognitionResult(rank="Unknown", level=0, confidence=0.0)

    def _extract_result(self, content: str) -> RecognitionResult:
        json_str = content.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        data = json.loads(json_str)
        return RecognitionResult(
            rank=data.get("rank", "Unknown"),
            level=int(data.get("level", 0)),
            confidence=float(data.get("confidence", 0.0))
        )


class ZhipuStrategy(APIStrategy):
    """智谱 AI API策略"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def call(self, image_base64: str, prompt: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            "stream": False,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    async def acall(self, image_base64: str, prompt: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            "stream": False,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                response.raise_for_status()
                return await response.json()

    def parse_response(self, response: dict) -> RecognitionResult:
        try:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return self._extract_result(content)
        except (KeyError, IndexError, json.JSONDecodeError):
            return RecognitionResult(rank="Unknown", level=0, confidence=0.0)

    def _extract_result(self, content: str) -> RecognitionResult:
        json_str = content.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        data = json.loads(json_str)
        return RecognitionResult(
            rank=data.get("rank", "Unknown"),
            level=int(data.get("level", 0)),
            confidence=float(data.get("confidence", 0.0))
        )


# ==================== 策略工厂 ====================

class APIStrategyFactory:
    """API策略工厂，根据配置创建对应的策略"""

    @staticmethod
    def create(
        api_key: str,
        api_base_url: str,
        api_model: str,
        api_type: str = None,
    ) -> APIStrategy:
        # 自动识别api_type
        if api_type is None:
            if "volces.com" in api_base_url or "ark.cn" in api_base_url:
                api_type = "doubao"
            elif "bigmodel.cn" in api_base_url or "zhipuai" in api_base_url:
                api_type = "zhipu"
            else:
                api_type = "doubao"  # 默认

        if api_type == "doubao":
            return DoubaoStrategy(api_key, api_base_url, api_model)
        elif api_type == "zhipu":
            return ZhipuStrategy(api_key, api_base_url, api_model)
        else:
            raise ValueError(f"Unsupported API type: {api_type}")


# ==================== 主识别器 ====================

class AIAwareLegendRecognizer:
    """游戏段位图标识别器，支持多种AI API"""

    # 预定义的API类型常量
    API_TYPE_DOUBAO = "doubao"
    API_TYPE_ZHIPU = "zhipu"

    # 保存选项标志位（二进制组合）
    SAVE_NONE = 0b00       # 都不保存
    SAVE_UNKNOWN = 0b01    # 只保存 Unknown
    SAVE_LEGENDARY = 0b10  # 只保存 Legendary
    SAVE_ALL = 0b11        # 都保存（默认）

    def __init__(
        self,
        api_key: str,
        api_base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        api_model: str = "doubao-seed-2-0-pro-260215",
        api_type: str = None,
        legend_dir: str = "data/legend",
        unknown_dir: str = "data/unknown",
        auto_crop: bool = False,
        save_flags: int = None,           # 新增：保存选项标志
        save_unknown_with_url: bool = False,  # 新增：Unknown 文件名是否包含 URL
        legend_counter: int = 0,          # 新增：Legendary 计数器初始值
        unknown_counter: int = 0,         # 新增：Unknown 计数器初始值
    ):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.api_model = api_model
        self.api_type = api_type
        self.legend_dir = Path(legend_dir)
        self.unknown_dir = Path(unknown_dir)
        self.auto_crop = auto_crop

        # 设置默认 save_flags
        if save_flags is None:
            save_flags = self.SAVE_ALL

        # 验证 save_flags 参数
        if not isinstance(save_flags, int) or save_flags < 0 or save_flags > self.SAVE_ALL:
            raise ValueError(
                f"save_flags must be one of: "
                f"SAVE_NONE({self.SAVE_NONE}), SAVE_UNKNOWN({self.SAVE_UNKNOWN}), "
                f"SAVE_LEGENDARY({self.SAVE_LEGENDARY}), SAVE_ALL({self.SAVE_ALL})"
            )

        self._save_flags = save_flags
        self._save_unknown_with_url = save_unknown_with_url
        self._legend_counter = legend_counter
        self._unknown_counter = unknown_counter

        # 创建API策略
        self._api_strategy = APIStrategyFactory.create(
            api_key, api_base_url, api_model, api_type
        )

        self.legend_dir.mkdir(parents=True, exist_ok=True)
        self.unknown_dir.mkdir(parents=True, exist_ok=True)

    def _load_image(self, source) -> np.ndarray:
        """Load image from file path, URL, or numpy array."""
        if isinstance(source, np.ndarray):
            return source
        if isinstance(source, str):
            if source.startswith("http://") or source.startswith("https://"):
                response = requests.get(source)
                response.raise_for_status()
                img = Image.open(io.BytesIO(response.content))
                return np.array(img)
            else:
                img = Image.open(source)
                return np.array(img)
        raise ValueError(f"Unsupported image source type: {type(source)}")

    def _crop_image(self, img: np.ndarray) -> np.ndarray:
        """Crop image using CROP_REGION (relative coordinates)."""
        h, w = img.shape[:2]
        x1 = int(CROP_REGION["x1"] * w)
        y1 = int(CROP_REGION["y1"] * h)
        x2 = int(CROP_REGION["x2"] * w)
        y2 = int(CROP_REGION["y2"] * h)
        return img[y1:y2, x1:x2]

    def _recognize(self, img: np.ndarray) -> RecognitionResult:
        """Full recognition pipeline: encode image and call API."""
        _, buffer = cv2.imencode(".png", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        image_base64 = base64.b64encode(buffer).decode("utf-8")
        response = self._api_strategy.call(image_base64, LEGENDARY_PROMPT)
        return self._api_strategy.parse_response(response)

    def _save_image(self, img: np.ndarray, rank: str, level: int) -> str:
        """保存图片到对应目录"""
        if rank == "Legendary":
            filename = f"Legend_{level}_{self._legend_counter:03d}.png"
            filepath = self.legend_dir / filename
            self._legend_counter += 1
        else:
            filename = f"Unknown_{self._unknown_counter:03d}.png"
            filepath = self.unknown_dir / filename
            self._unknown_counter += 1
        # 转换为 BGR (cv2.imwrite expects BGR)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(filepath), img_bgr)
        return str(filepath)

    def recognize_ai(self, image_source) -> RecognitionResult:
        """识别单张图片"""
        img = self._load_image(image_source)
        if img is None:
            return RecognitionResult("Unknown", 0, 0.0)
        crop = self._crop_image(img) if self.auto_crop else img
        result = self._recognize(crop)
        self._save_image(crop, result.rank, result.level)
        return result

    def recognize_batch_ai(self, sources: List[str]) -> List[RecognitionResult]:
        """批量识别"""
        return [self.recognize_ai(src) for src in sources]

    # ==================== Async Methods ====================

    async def _arecognize(self, img: np.ndarray) -> RecognitionResult:
        """Async full recognition pipeline."""
        _, buffer = cv2.imencode(".png", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        image_base64 = base64.b64encode(buffer).decode("utf-8")
        response = await self._api_strategy.acall(image_base64, LEGENDARY_PROMPT)
        return self._api_strategy.parse_response(response)

    async def recognize_ai_async(self, image_source) -> RecognitionResult:
        """Async识别单张图片"""
        img = self._load_image(image_source)
        if img is None:
            return RecognitionResult("Unknown", 0, 0.0)
        crop = self._crop_image(img) if self.auto_crop else img
        result = await self._arecognize(crop)
        self._save_image(crop, result.rank, result.level)
        return result

    async def recognize_batch_ai_async(self, sources: List[str]) -> List[RecognitionResult]:
        """Async批量识别"""
        tasks = [self.recognize_ai_async(src) for src in sources]
        return await asyncio.gather(*tasks)
