# Legend Recognizer

游戏段位图标识别模块，专注于传奇(Legendary)段位识别。

## 安装

### 从 Git 仓库直接安装

```bash
pip install git+https://github.com/frigidom1024/rank_detector.git
```

### 从源码安装

```bash
git clone git@github.com:frigidom1024/rank_detector.git
cd rank_detector
pip install -e .
```

## 快速开始

```python
from core import AIAwareLegendRecognizer

# 初始化
recognizer = AIAwareLegendRecognizer(
    api_key="your_api_key",
    api_base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_model="doubao-seed-2-0-pro-260215",
    legend_dir="data/legend",      # 传奇图片保存目录
    unknown_dir="data/unknown",    # 非传奇图片保存目录
    auto_crop=False,               # 是否自动裁剪左上角图标区域
)

# 同步识别
result = recognizer.recognize_ai("test.png")
print(f"Rank: {result.rank}, Level: {result.level}, Confidence: {result.confidence}")

# 批量识别
results = recognizer.recognize_batch_ai(["img1.png", "img2.png"])

# 异步识别
import asyncio
async def async_recognize():
    result = await recognizer.recognize_ai_async("test.png")
    return result

result = asyncio.run(async_recognize())

# 异步批量识别
async def async_batch():
    results = await recognizer.recognize_batch_ai_async(["img1.png", "img2.png"])
    return results

results = asyncio.run(async_batch())
```

## RecognitionResult

| 字段 | 类型 | 说明 |
|------|------|------|
| rank | str | "Legendary" 或 "Unknown" |
| level | int | 传奇排名，非传奇为 0 |
| confidence | float | 置信度 0-1 |

## 目录结构

```
data/
├── legend/           # 传奇图片 Legend_{level}_{id}.png
│   └── Legend_5286_001.png
└── unknown/          # 非传奇图片 Unknown_{id}.png
    └── Unknown_001.png
```
