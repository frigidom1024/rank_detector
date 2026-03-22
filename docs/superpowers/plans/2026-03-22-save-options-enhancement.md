# 保存功能增强实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 增强图片保存功能，支持二进制标志位控制保存类型，以及 Unknown 图片文件名包含 URL

**架构:** 在 `AIAwareLegendRecognizer` 类中添加保存标志常量和相关参数，修改 `_save_image` 方法支持条件保存和 URL 后缀，新增 URL 提取和清理辅助方法

**技术栈:** Python 3.10+, pathlib, urllib.parse

---

## Chunk 1: 添加保存标志常量和初始化参数

**文件:**
- Modify: `rank_detector_core/legend_recognizer.py:264-297`
- Note: Optional 和 List 已在文件开头导入，无需额外导入

### Task 1: 添加保存标志常量

- [ ] **Step 1: 在类开头添加保存标志常量**

在 `AIAwareLegendRecognizer` 类的 API 类型常量后添加：

```python
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
```

- [ ] **Step 2: 运行 Python 语法检查**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python -m py_compile rank_detector_core/legend_recognizer.py
```

Expected: 无错误输出

- [ ] **Step 3: 提交**

```bash
git add rank_detector_core/legend_recognizer.py
git commit -m "feat: 添加保存标志常量"
```

### Task 2: 扩展初始化方法参数

- [ ] **Step 1: 修改 __init__ 方法签名和实现**

将 `__init__` 方法修改为：

```python
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
```

- [ ] **Step 2: 运行 Python 语法检查**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python -m py_compile rank_detector_core/legend_recognizer.py
```

Expected: 无错误输出

- [ ] **Step 3: 提交**

```bash
git add rank_detector_core/legend_recognizer.py
git commit -m "feat: 扩展初始化方法参数"
```

---

## Chunk 2: 添加 URL 处理辅助方法

**文件:**
- Modify: `rank_detector_core/legend_recognizer.py` (在 `_crop_image` 方法后添加)

### Task 3: 添加 _extract_url 方法

- [ ] **Step 1: 在 _crop_image 方法后添加 _extract_url 方法**

```python
def _extract_url(self, image_source) -> Optional[str]:
    """从 image_source 中提取 URL（仅当它是 HTTP(S) URL 时）"""
    # 字符串 URL
    if isinstance(image_source, str):
        if image_source.startswith("http://") or image_source.startswith("https://"):
            return image_source
    # 其他类型不视为 URL
    return None
```

- [ ] **Step 2: 运行 Python 语法检查**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python -m py_compile rank_detector_core/legend_recognizer.py
```

Expected: 无错误输出

- [ ] **Step 3: 提交**

```bash
git add rank_detector_core/legend_recognizer.py
git commit -m "feat: 添加 URL 提取方法"
```

### Task 4: 添加 _sanitize_url 方法

- [ ] **Step 1: 在 _extract_url 方法后添加 _sanitize_url 方法**

```python
def _sanitize_url(self, url: str) -> str:
    """清理 URL 使其适合作为文件名"""
    from urllib.parse import unquote

    # 移除协议前缀
    url = url.replace("http://", "").replace("https://", "")

    # URL 解码（处理 %20 等）
    url = unquote(url)

    # 替换不安全字符
    unsafe_chars = '/:?#\\\'"<>|*'
    for char in unsafe_chars:
        url = url.replace(char, '_')

    # 限制长度（避免文件名过长）
    return url[:100].strip()
```

- [ ] **Step 2: 运行 Python 语法检查**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python -m py_compile rank_detector_core/legend_recognizer.py
```

Expected: 无错误输出

- [ ] **Step 3: 提交**

```bash
git add rank_detector_core/legend_recognizer.py
git commit -m "feat: 添加 URL 清理方法"
```

---

## Chunk 3: 修改 _save_image 方法

**文件:**
- Modify: `rank_detector_core/legend_recognizer.py:330-343`

### Task 5: 重写 _save_image 方法

- [ ] **Step 1: 替换 _save_image 方法实现**

将整个 `_save_image` 方法替换为：

```python
def _save_image(
    self,
    img: np.ndarray,
    rank: str,
    level: int,
    original_url: str = None,
    save_flags: int = None
) -> Optional[str]:
    """保存图片到对应目录，返回文件路径或 None

    注意：计数器仅在成功保存后递增，不保存时计数器不变
    """

    # 使用传入的 save_flags 或实例默认值
    flags = save_flags if save_flags is not None else self._save_flags

    # 确定是否需要保存
    if rank == "Legendary":
        should_save = flags & self.SAVE_LEGENDARY
    else:  # Unknown 或其他值都视为 Unknown
        should_save = flags & self.SAVE_UNKNOWN

    if not should_save:
        return None

    # 构建文件名（在确认保存后才递增计数器，避免编号断层）
    if rank == "Legendary":
        filename = f"Legend_{level}_{self._legend_counter:03d}"
        self._legend_counter += 1
    else:
        filename = f"Unknown_{self._unknown_counter:03d}"
        self._unknown_counter += 1

        # Unknown 图片：如果启用且存在 URL，添加到文件名
        if self._save_unknown_with_url and original_url:
            clean_url = self._sanitize_url(original_url)
            if clean_url:  # 只有清理后有内容才添加
                filename = f"{filename}_url_{clean_url}"

    filename += ".png"

    # 确定保存目录并保存
    save_dir = self.legend_dir if rank == "Legendary" else self.unknown_dir
    filepath = save_dir / filename

    try:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(filepath), img_bgr)
    except OSError as e:
        print(f"Warning: Failed to save image to {filepath}: {e}")
        return None

    return str(filepath)
```

- [ ] **Step 2: 运行 Python 语法检查**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python -m py_compile rank_detector_core/legend_recognizer.py
```

Expected: 无错误输出

- [ ] **Step 3: 提交**

```bash
git add rank_detector_core/legend_recognizer.py
git commit -m "feat: 重写保存图片方法支持条件保存和URL后缀"
```

---

## Chunk 4: 修改同步识别方法

**文件:**
- Modify: `rank_detector_core/legend_recognizer.py:345-353`

### Task 6: 修改 recognize_ai 方法

- [ ] **Step 1: 更新 recognize_ai 方法**

```python
def recognize_ai(self, image_source, save_flags: int = None) -> RecognitionResult:
    """识别单张图片"""
    # 提取 URL（如果是网络图片）
    original_url = self._extract_url(image_source)

    img = self._load_image(image_source)
    if img is None:
        return RecognitionResult("Unknown", 0, 0.0)

    crop = self._crop_image(img) if self.auto_crop else img
    result = self._recognize(crop)

    # 保存时传递原始 URL 和 save_flags
    self._save_image(crop, result.rank, result.level, original_url, save_flags)

    return result
```

- [ ] **Step 2: 运行 Python 语法检查**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python -m py_compile rank_detector_core/legend_recognizer.py
```

Expected: 无错误输出

- [ ] **Step 3: 提交**

```bash
git add rank_detector_core/legend_recognizer.py
git commit -m "feat: 更新同步识别方法"
```

### Task 7: 修改 recognize_batch_ai 方法

- [ ] **Step 1: 更新 recognize_batch_ai 方法**

```python
def recognize_batch_ai(self, sources: List[str], save_flags: int = None) -> List[RecognitionResult]:
    """批量识别"""
    return [self.recognize_ai(src, save_flags) for src in sources]
```

- [ ] **Step 2: 运行 Python 语法检查**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python -m py_compile rank_detector_core/legend_recognizer.py
```

Expected: 无错误输出

- [ ] **Step 3: 提交**

```bash
git add rank_detector_core/legend_recognizer.py
git commit -m "feat: 更新批量识别方法"
```

---

## Chunk 5: 修改异步识别方法

**文件:**
- Modify: `rank_detector_core/legend_recognizer.py` (异步方法部分)

### Task 8: 修改 recognize_ai_async 方法

- [ ] **Step 1: 更新 recognize_ai_async 方法**

```python
async def recognize_ai_async(self, image_source, save_flags: int = None) -> RecognitionResult:
    """Async识别单张图片"""
    # 提取 URL（如果是网络图片）
    original_url = self._extract_url(image_source)

    img = self._load_image(image_source)
    if img is None:
        return RecognitionResult("Unknown", 0, 0.0)

    crop = self._crop_image(img) if self.auto_crop else img
    result = await self._arecognize(crop)

    # 保存时传递原始 URL 和 save_flags
    self._save_image(crop, result.rank, result.level, original_url, save_flags)

    return result
```

- [ ] **Step 2: 运行 Python 语法检查**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python -m py_compile rank_detector_core/legend_recognizer.py
```

Expected: 无错误输出

- [ ] **Step 3: 提交**

```bash
git add rank_detector_core/legend_recognizer.py
git commit -m "feat: 更新异步识别方法"
```

### Task 9: 修改 recognize_batch_ai_async 方法

- [ ] **Step 1: 更新 recognize_batch_ai_async 方法**

```python
async def recognize_batch_ai_async(self, sources: List[str], save_flags: int = None) -> List[RecognitionResult]:
    """Async批量识别"""
    tasks = [self.recognize_ai_async(src, save_flags) for src in sources]
    return await asyncio.gather(*tasks)
```

- [ ] **Step 2: 运行 Python 语法检查**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python -m py_compile rank_detector_core/legend_recognizer.py
```

Expected: 无错误输出

- [ ] **Step 3: 提交**

```bash
git add rank_detector_core/legend_recognizer.py
git commit -m "feat: 更新异步批量识别方法"
```

---

## Chunk 6: 更新 __init__.py 导出

**文件:**
- Modify: `rank_detector_core/__init__.py`

### Task 10: 导出保存标志常量

- [ ] **Step 1: 更新 __init__.py**

将 `__init__.py` 更新为：

```python
from .legend_recognizer import (
    AIAwareLegendRecognizer,
    RecognitionResult,
)

# 保存标志常量也可以直接导入
SAVE_NONE = AIAwareLegendRecognizer.SAVE_NONE
SAVE_UNKNOWN = AIAwareLegendRecognizer.SAVE_UNKNOWN
SAVE_LEGENDARY = AIAwareLegendRecognizer.SAVE_LEGENDARY
SAVE_ALL = AIAwareLegendRecognizer.SAVE_ALL

__all__ = [
    "AIAwareLegendRecognizer",
    "RecognitionResult",
    "SAVE_NONE",
    "SAVE_UNKNOWN",
    "SAVE_LEGENDARY",
    "SAVE_ALL",
]
```

- [ ] **Step 2: 运行 Python 导入测试**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python -c "from rank_detector_core import SAVE_ALL, AIAwareLegendRecognizer; print(f'SAVE_ALL={SAVE_ALL}')"
```

Expected: `SAVE_ALL=3`

- [ ] **Step 3: 提交**

```bash
git add rank_detector_core/__init__.py
git commit -m "feat: 导出保存标志常量"
```

---

## Chunk 7: 更新 README 文档

**文件:**
- Modify: `README.md:39-53` (在快速开始代码块后添加说明)

### Task 11: 更新使用文档

- [ ] **Step 1: 在快速开始部分添加新参数说明**

在 `recognizer = AIAwareLegendRecognizer(...)` 初始化代码后（大约第 39 行后）添加注释说明：

在 `recognizer = AIAwareLegendRecognizer(...)` 初始化代码后添加：

```python
# 支持的模型类型:
# - 豆包/火山引擎: api_base_url 包含 "volces.com" 或 "ark.cn"
# - 智谱AI: api_base_url 包含 "bigmodel.cn" 或 "zhipuai"
# 也可通过 api_type 参数显式指定: "doubao" 或 "zhipu"

# 保存选项（使用二进制标志位组合）:
# - SAVE_NONE=0: 都不保存
# - SAVE_UNKNOWN=1: 只保存 Unknown
# - SAVE_LEGENDARY=2: 只保存 Legendary
# - SAVE_ALL=3: 都保存（默认）
#
# save_unknown_with_url: Unknown 文件名是否包含原始 URL
# recognizer = AIAwareLegendRecognizer(
#     ...,
#     save_flags=SAVE_UNKNOWN,        # 只保存 Unknown
#     save_unknown_with_url=True,     # 文件名包含 URL
# )
#
# 调用时临时覆盖:
# result = recognizer.recognize_ai(
#     "image.png",
#     save_flags=SAVE_LEGENDARY  # 这次只保存 Legendary
# )
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: 更新使用文档"
```

---

## Chunk 8: 手动测试验证

**文件:**
- Test: 手动运行测试脚本

### Task 12: 创建并运行测试脚本

- [ ] **Step 1: 创建测试脚本**

创建 `test_save_features.py`:

```python
"""测试保存功能增强"""
import sys
import os
sys.path.insert(0, 'd:/project/rank_detector')

from rank_detector_core import AIAwareLegendRecognizer, SAVE_ALL, SAVE_UNKNOWN, SAVE_LEGENDARY, SAVE_NONE

# 从 .env 文件读取 API 配置
api_key = os.environ.get('DOUBAO_API_KEY', '1ab20cc0-3735-4b11-8728-ea52dcae2fe0')
api_base_url = os.environ.get('DOUBAO_API_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3')
api_model = os.environ.get('DOUBAO_API_MODEL', 'doubao-seed-2-0-pro-260215')

print("=" * 50)
print("保存功能增强测试")
print("=" * 50)

# 测试 1: 默认行为（保存所有）
print("\n测试 1: 默认行为")
recognizer = AIAwareLegendRecognizer(
    api_key=api_key,
    api_base_url=api_base_url,
    api_model=api_model,
    legend_dir="data/test_legend",
    unknown_dir="data/test_unknown",
)
print(f"  save_flags = {recognizer._save_flags} (expected {SAVE_ALL})")
print(f"  save_unknown_with_url = {recognizer._save_unknown_with_url} (expected False)")

# 测试 2: 只保存 Unknown
print("\n测试 2: 只保存 Unknown")
recognizer = AIAwareLegendRecognizer(
    api_key=api_key,
    api_base_url=api_base_url,
    api_model=api_model,
    save_flags=SAVE_UNKNOWN,
)
print(f"  save_flags = {recognizer._save_flags} (expected {SAVE_UNKNOWN})")

# 测试 3: URL 提取
print("\n测试 3: URL 提取")
url = recognizer._extract_url("https://example.com/image.png")
print(f"  URL extracted: {url}")
assert url == "https://example.com/image.png", "URL 提取失败"

local = recognizer._extract_url("/path/to/image.png")
print(f"  Local file: {local}")
assert local is None, "本地文件不应返回 URL"

# 测试 4: URL 清理
print("\n测试 4: URL 清理")
clean = recognizer._sanitize_url("https://example.com/path/to/image.png?query=value")
print(f"  Cleaned URL: {clean}")
assert "http" not in clean, "协议应该被移除"
assert "?" not in clean or "_" in clean, "特殊字符应该被替换"

# 测试 5: 无效 save_flags 抛出异常
print("\n测试 5: 无效 save_flags 抛出异常")
try:
    recognizer = AIAwareLegendRecognizer(
        api_key=api_key,
        api_base_url=api_base_url,
        api_model=api_model,
        save_flags=99,  # 无效值
    )
    print("  ERROR: 应该抛出 ValueError")
    assert False, "应该抛出 ValueError"
except ValueError as e:
    print(f"  Caught expected ValueError")

# 测试 6: 实际图片识别测试（使用豆包 API）
print("\n测试 6: 实际图片识别测试")
print("  使用现有测试图片进行识别...")

# 检查是否有测试图片
test_image = "data/legend/Legend_1898_000.png"
if os.path.exists(test_image):
    recognizer = AIAwareLegendRecognizer(
        api_key=api_key,
        api_base_url=api_base_url,
        api_model=api_model,
        legend_dir="data/test_output_legend",
        unknown_dir="data/test_output_unknown",
        save_flags=SAVE_ALL,
        save_unknown_with_url=False,
    )

    result = recognizer.recognize_ai(test_image)
    print(f"  识别结果: rank={result.rank}, level={result.level}, confidence={result.confidence}")

    # 检查文件是否保存
    if os.path.exists("data/test_output_legend"):
        files = os.listdir("data/test_output_legend")
        print(f"  保存的文件: {files}")
else:
    print(f"  跳过: 测试图片不存在 ({test_image})")

# 测试 7: save_flags 临时覆盖
print("\n测试 7: save_flags 临时覆盖")
recognizer = AIAwareLegendRecognizer(
    api_key=api_key,
    api_base_url=api_base_url,
    api_model=api_model,
    save_flags=SAVE_ALL,
    legend_dir="data/test_output_legend2",
    unknown_dir="data/test_output_unknown2",
)

# 获取当前计数
legend_count_before = recognizer._legend_counter
print(f"  Legend counter before: {legend_count_before}")

# 使用 SAVE_NONE 不保存
if os.path.exists(test_image):
    result = recognizer.recognize_ai(test_image, save_flags=SAVE_NONE)
    legend_count_after = recognizer._legend_counter
    print(f"  Legend counter after SAVE_NONE: {legend_count_after}")
    assert legend_count_before == legend_count_after, "SAVE_NONE 时计数器不应递增"
    print("  SAVE_NONE 正常工作")

print("\n" + "=" * 50)
print("所有测试通过！")
print("=" * 50)
```

- [ ] **Step 2: 运行测试**

```bash
cd d:/project/rank_detector
D:/InstallPath/miniconda/envs/rank_detector/python test_save_features.py
```

Expected: 所有测试通过，实际识别并保存图片

- [ ] **Step 3: 验证保存的文件**

```bash
# 检查测试输出目录
ls -la d:/project/rank_detector/data/test_output_legend/
ls -la d:/project/rank_detector/data/test_output_unknown/
```

- [ ] **Step 4: 清理测试文件和目录**

```bash
rm d:/project/rank_detector/test_save_features.py
rm -rf d:/project/rank_detector/data/test_output_legend/
rm -rf d:/project/rank_detector/data/test_output_unknown/
rm -rf d:/project/rank_detector/data/test_legend/
rm -rf d:/project/rank_detector/data/test_unknown/
rm -rf d:/project/rank_detector/data/test_output_legend2/
rm -rf d:/project/rank_detector/data/test_output_unknown2/
```

- [ ] **Step 5: 提交最终实现**

```bash
git add -A
git commit -m "feat: 完成保存功能增强实现"
```

---

## 实现完成检查清单

- [ ] 所有保存标志常量已定义
- [ ] 初始化方法支持所有新参数
- [ ] save_flags 参数验证正常工作
- [ ] URL 提取方法正确识别 HTTP(S) URL
- [ ] URL 清理方法处理特殊字符和长度限制
- [ ] _save_image 方法支持条件保存
- [ ] _save_image 方法支持 URL 后缀（仅 Unknown）
- [ ] 计数器仅在保存时递增
- [ ] 同步识别方法传递 URL 和 save_flags
- [ ] 异步识别方法传递 URL 和 save_flags
- [ ] README 文档已更新
- [ ] 向后兼容性保持（默认值与原行为一致）
