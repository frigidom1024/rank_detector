"""
豆包 (Doubao) 图标识别工具
使用火山引擎豆包2.0模型识别裁剪后的段位图标

API 格式参考火山引擎文档
"""
import base64
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import cv2
import requests


# ============================================
# 配置
# ============================================

VOLCENGINE_CONFIG = {
    "api_key": os.environ.get("VOLCENGINE_API_KEY", ""),
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "doubao-seed-1-6-vision-250815",  # 视觉模型
}

# 截取区域配置 (百分比)
CROP_REGION = {
    "x1": 0.00,
    "y1": 0.00,
    "x2": 0.10,
    "y2": 0.25,
}

# ============================================


@dataclass
class IconResult:
    """识别结果"""
    rank: str
    level: int
    confidence: float


def encode_image_to_base64(image_path: str) -> str:
    """将图片编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def encode_image_from_array(img) -> str:
    """将 numpy 数组编码为 base64"""
    _, buffer = cv2.imencode('.png', img)
    return base64.b64encode(buffer).decode("utf-8")


def crop_image(img, region=CROP_REGION) -> tuple:
    """裁剪图片中的图标区域"""
    h, w = img.shape[:2]
    x1 = int(w * region["x1"])
    y1 = int(h * region["y1"])
    x2 = int(w * region["x2"])
    y2 = int(h * region["y2"])
    return img[y1:y2, x1:x2], (x1, y1, x2, y2)


def call_doubao_api(image_base64: str, prompt: str) -> Optional[Dict]:
    """调用豆包 API (新格式)"""
    if not VOLCENGINE_CONFIG["api_key"]:
        print("错误: 请设置 VOLCENGINE_API_KEY 环境变量")
        return None

    headers = {
        "Authorization": f"Bearer {VOLCENGINE_CONFIG['api_key']}",
        "Content-Type": "application/json",
    }

    # 使用 responses 端点
    payload = {
        "model": VOLCENGINE_CONFIG["model"],
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_base64}"
                    },
                    {
                        "type": "input_text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            f"{VOLCENGINE_CONFIG['base_url']}/responses",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print(f"API 错误: {response.status_code} - {response.text}")
            return None

        return response.json()

    except Exception as e:
        print(f"错误: {e}")
        return None


def create_prompt() -> str:
    """识别提示词"""
    return """这是一个游戏段位图标，请识别其段位和等级。

段位视觉特征:
- Bronze (青铜): 深灰/青铜色基底，造型朴素，无特效，下方罗马数字（如 Ⅲ）代表小段位
- Silver (白银): 银白/浅灰基底，边缘带淡蓝微光，造型简洁，下方罗马数字（如 Ⅱ）代表小段位
- Gold (黄金): 亮金色基底，边缘带暖黄微光，造型华丽，下方罗马数字（如 Ⅰ）代表小段位
- Diamond (钻石): 深紫/靛蓝基底，带水晶棱面特效，造型尖锐，下方罗马数字（如 Ⅲ）代表小段位
- Legendary (传奇): 红金火焰基底，顶部红水晶+金色边框，底部火焰纹理，下方赛季排名数字（如 3163）

请以 JSON 格式返回识别结果:
{"rank": "Gold", "level": 3, "confidence": 0.95}

只返回 JSON，不要其他内容。"""


def parse_response(response: Dict) -> Optional[IconResult]:
    """解析响应"""
    try:
        # 新格式: output 中有多个元素，找 type=message 的
        content = ""
        for item in response.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        content = c.get("text", "")
                        break

        if not content:
            print("错误: 响应中没有文本内容")
            print(f"响应 keys: {response.keys()}")
            return None

        # 去除 markdown 代码块
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())

        return IconResult(
            rank=data.get("rank", ""),
            level=int(data.get("level", 0)),
            confidence=float(data.get("confidence", 0.0))
        )

    except Exception as e:
        print(f"解析错误: {e}")
        print(f"原始响应: {response}")
        return None


def recognize_icon(img) -> Optional[IconResult]:
    """
    识别单个图标

    Args:
        img: 裁剪后的图标图片 (numpy array)

    Returns:
        IconResult 或 None
    """
    image_base64 = encode_image_from_array(img)
    response = call_doubao_api(image_base64, create_prompt())

    if response is None:
        return None

    return parse_response(response)


def recognize_from_file(image_path: str, auto_crop: bool = True) -> Optional[IconResult]:
    """
    从文件识别图标

    Args:
        image_path: 图片路径
        auto_crop: 是否自动裁剪 (默认True，使用CROP_REGION)

    Returns:
        IconResult 或 None
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"错误: 无法读取图片 {image_path}")
        return None

    if auto_crop:
        img_crop, coords = crop_image(img)
        print(f"裁剪区域: x=[{coords[0]}:{coords[2]}], y=[{coords[1]}:{coords[3]}]")
    else:
        img_crop = img

    return recognize_icon(img_crop)


def recognize_from_array(img, auto_crop: bool = True) -> Optional[IconResult]:
    """
    从 numpy 数组识别图标

    Args:
        img: 图片数组 (BGR)
        auto_crop: 是否自动裁剪

    Returns:
        IconResult 或 None
    """
    if auto_crop:
        img_crop, coords = crop_image(img)
    else:
        img_crop = img

    return recognize_icon(img_crop)


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("=" * 60)
        print("豆包图标识别工具")
        print("=" * 60)
        print()
        print("用法: python doubao_recognizer.py <图片路径>")
        print()
        print("环境变量: set VOLCENGINE_API_KEY=your_key")
        print("=" * 60)
        sys.exit(1)

    # 检查 API Key
    if not VOLCENGINE_CONFIG["api_key"]:
        print("错误: 请设置 VOLCENGINE_API_KEY")
        print("获取地址: https://www.volcengine.com/docs/doubao/1301394")
        sys.exit(1)

    image_path = sys.argv[1]

    print(f"识别图片: {image_path}")

    result = recognize_from_file(image_path, auto_crop=True)

    if result:
        print(f"\n结果: {result.rank} {result.level}")
        print(f"置信度: {result.confidence:.0%}")
    else:
        print("\n识别失败")


if __name__ == "__main__":
    main()
