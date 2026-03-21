"""
下载 YOLOv8 预训练模型
使用国内镜像源
"""
import os
from pathlib import Path
from urllib.request import urlretrieve

# 模型下载地址（使用镜像源）
MODELS = {
    "yolov8n.pt": "https://ghproxy.com/https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt",
    "yolov8s.pt": "https://ghproxy.com/https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s.pt",
    "yolov8m.pt": "https://ghproxy.com/https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8m.pt",
}

def download_model(model_name="yolov8n.pt"):
    """下载预训练模型"""
    # Ultralytics 会自动将模型缓存到这个目录
    cache_dir = Path.home() / ".cache" / "ultralytics"
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_path = cache_dir / model_name

    if model_path.exists():
        print(f"模型已存在: {model_path}")
        return model_path

    url = MODELS.get(model_name)
    if not url:
        print(f"未知模型: {model_name}")
        return None

    print(f"正在下载 {model_name}...")
    print(f"来源: {url}")

    try:
        urlretrieve(url, model_path)
        print(f"下载完成: {model_path}")
        return model_path
    except Exception as e:
        print(f"下载失败: {e}")
        return None

if __name__ == "__main__":
    # 下载 nano 模型（最小，最快）
    download_model("yolov8n.pt")
