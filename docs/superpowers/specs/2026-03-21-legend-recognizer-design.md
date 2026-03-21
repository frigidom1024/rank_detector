# AIAware Legend Recognizer 模块设计

> **目标:** 创建一个专注于传奇(Legendary)段位识别的 AI 模块

## 概述

通过传入图片（本地路径/URL），自动裁剪 ROI 区域，使用 AI 模型识别是否为传奇段位及排名，保存结果图片。

## API 设计

```python
from core.legend_recognizer import AIAwareLegendRecognizer, RecognitionResult

# 初始化（可配置 API 和路径）
recognizer = AIAwareLegendRecognizer(
    api_key="your_key",                              # API 密钥
    api_base_url="https://ark.cn-beijing.volces.com/api/v3",  # API 地址
    api_model="doubao-seed-2-0-pro-260215",         # 模型
    legend_dir="data/legend",                        # 传奇图片输出目录
    unknown_dir="data/unknown",                      # 非传奇图片输出目录
)

# 单张识别
result = recognizer.recognize_ai("test.png")                    # 本地文件
result = recognizer.recognize_ai("https://example.com/img.png") # URL

# 批量识别
results = recognizer.recognize_batch_ai(["img1.png", "img2.png"])
```

### RecognitionResult 数据类

```python
@dataclass
class RecognitionResult:
    rank: str           # "Legendary" 或 "Unknown"
    level: int          # 传奇排名，或 0
    confidence: float   # 置信度 0-1
```

## 目录结构

```
data/
├── legend/           # 传奇图片 Legend_排名_id.png
│   └── Legend_5286_001.png
└── unknown/          # 非传奇图片 Unknown_id.png
    └── Unknown_001.png
```

## 核心流程

1. **输入处理** - 支持本地路径、URL、numpy 数组
2. **图片下载** - 如果是 URL，下载到临时文件
3. **ROI 裁剪** - 按配置的区域裁剪图标区域
4. **AI 识别** - 调用豆包 API 识别段位
5. **结果保存** - 根据识别结果保存到对应目录
   - Legendary → `legend_dir/Legend_{level}_{id}.png`
   - Unknown → `unknown_dir/Unknown_{id}.png`

## 文件命名

- **传奇:** `Legend_{排名}_{序号}.png`
  - 例: `Legend_5286_001.png`, `Legend_139_002.png`
- **非传奇:** `Unknown_{序号}.png`
  - 例: `Unknown_001.png`, `Unknown_002.png`

序号从 1 开始，自动递增。

## 配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `legend_dir` | `data/legend` | 传奇图片输出目录 |
| `unknown_dir` | `data/unknown` | 非传奇图片输出目录 |
| `crop_region` | `{"x1": 0.00, "y1": 0.00, "x2": 0.10, "y2": 0.25}` | 裁剪区域（百分比） |
| `api_model` | `doubao-seed-2-0-pro-260215` | 豆包模型 |

## 实现文件

- `core/legend_recognizer.py` - 主模块
