import base64
import json
import io
import requests
from typing import List, Dict, Optional
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


class AIAwareLegendRecognizer:
    def __init__(
        self,
        api_key: str,
        api_base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        api_model: str = "doubao-seed-2-0-pro-260215",
        legend_dir: str = "data/legend",
        unknown_dir: str = "data/unknown",
    ):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.api_model = api_model
        self.legend_dir = Path(legend_dir)
        self.unknown_dir = Path(unknown_dir)
        self._legend_counter = 0
        self._unknown_counter = 0

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

    def _call_api(self, image_base64: str, prompt: str) -> dict:
        """Call the Doubao API with image and prompt."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.api_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 256,
        }
        response = requests.post(
            f"{self.api_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _parse_response(self, response: dict) -> RecognitionResult:
        """Parse API response into RecognitionResult."""
        try:
            content = response["choices"][0]["message"]["content"]
            json_str = content.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            data = json.loads(json_str)
            rank = data.get("rank", "Unknown")
            level = int(data.get("level", 0))
            confidence = float(data.get("confidence", 0.0))
            return RecognitionResult(rank=rank, level=level, confidence=confidence)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return RecognitionResult(rank="Unknown", level=0, confidence=0.0)

    def _recognize(self, img: np.ndarray) -> RecognitionResult:
        """Full recognition pipeline: encode image and call API."""
        _, buffer = cv2.imencode(".png", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        image_base64 = base64.b64encode(buffer).decode("utf-8")
        response = self._call_api(image_base64, LEGENDARY_PROMPT)
        return self._parse_response(response)

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
        cv2.imwrite(str(filepath), img)
        return str(filepath)

    def recognize_ai(self, image_source) -> RecognitionResult:
        """识别单张图片"""
        img = self._load_image(image_source)
        if img is None:
            return RecognitionResult("Unknown", 0, 0.0)
        crop = self._crop_image(img)
        result = self._recognize(crop)
        self._save_image(crop, result.rank, result.level)
        return result

    def recognize_batch_ai(self, sources: List[str]) -> List[RecognitionResult]:
        """批量识别"""
        return [self.recognize_ai(src) for src in sources]