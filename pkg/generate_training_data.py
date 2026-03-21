import os
import json
import random
import shutil
from pathlib import Path
from collections import defaultdict

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

# 配置
CONFIG = {
    "images_per_class": 100,  # 每个类别生成的图片数
    "icon_size": (64, 64),  # 图标基础大小
    "canvas_size": (640, 480),  # 画布大小
    "train_ratio": 0.7,
    "val_ratio": 0.2,
    "test_ratio": 0.1,
}

# 类别定义：段位 -> (class_id_start, levels)
# 格式: 段位名称: (起始类别ID, 等级列表)
# Legendary 统一为一类，后续用OCR识别排名数字
CLASSES = {
    "Bronze": (0, [1, 2, 3, 4, 5]),
    "Silver": (5, [1, 2, 3, 4, 5]),
    "Gold": (10, [1, 2, 3, 4, 5]),
    "Diamond": (15, [1, 2, 3, 4, 5]),
    "Legendary": (20, [0]),  # Legendary统一为一类，用OCR识别排名
}

# 生成类别名称列表
CLASS_NAMES = []
for rank, (start_id, levels) in CLASSES.items():
    for level in levels:
        CLASS_NAMES.append(f"{rank}_{level}")

print(f"总类别数: {len(CLASS_NAMES)}")
print(f"类别列表: {CLASS_NAMES}")


def get_class_id(rank: str, level: int) -> int:
    """根据段位和等级获取类别ID"""
    start_id, levels = CLASSES[rank]
    if level in levels:
        return start_id + levels.index(level)
    # 如果level不在列表中，使用第一个
    return start_id


def create_random_background(width, height):
    """创建随机背景"""
    # 随机选择背景类型
    bg_type = random.choice(["solid", "gradient", "noise"])

    if bg_type == "solid":
        # 纯色背景
        color = [random.randint(0, 255) for _ in range(3)]
        return np.ones((height, width, 3), dtype=np.uint8) * np.array(color, dtype=np.uint8)

    elif bg_type == "gradient":
        # 渐变背景
        img = np.zeros((height, width, 3), dtype=np.uint8)
        color1 = [random.randint(0, 255) for _ in range(3)]
        color2 = [random.randint(0, 255) for _ in range(3)]
        for i in range(height):
            alpha = i / height
            color = [
                int(color1[j] * (1 - alpha) + color2[j] * alpha)
                for j in range(3)
            ]
            img[i, :] = color
        return img

    else:  # noise
        # 噪点背景
        noise = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        # 模糊处理
        return cv2.blur(noise, (20, 20))


def augment_icon(icon_img):
    """对图标进行数据增强"""
    # 转换为PIL格式
    if isinstance(icon_img, np.ndarray):
        icon_img = Image.fromarray(cv2.cvtColor(icon_img, cv2.COLOR_BGR2RGB))

    # 随机旋转
    if random.random() > 0.5:
        angle = random.uniform(-15, 15)
        icon_img = icon_img.rotate(angle, expand=False, fillcolor=(0, 0, 0, 0))

    # 随机缩放
    if random.random() > 0.5:
        scale = random.uniform(0.8, 1.2)
        w, h = icon_img.size
        new_w, new_h = int(w * scale), int(h * scale)
        icon_img = icon_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 亮度调整
    if random.random() > 0.5:
        enhancer = ImageEnhance.Brightness(icon_img)
        factor = random.uniform(0.8, 1.2)
        icon_img = enhancer.enhance(factor)

    # 对比度调整
    if random.random() > 0.5:
        enhancer = ImageEnhance.Contrast(icon_img)
        factor = random.uniform(0.8, 1.2)
        icon_img = enhancer.enhance(factor)

    # 添加轻微高斯模糊（模拟截图模糊）
    if random.random() > 0.7:
        icon_img = icon_img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0, 0.5)))

    return icon_img


def paste_icon_with_alpha(background, icon, x, y):
    """将带透明通道的图标粘贴到背景上"""
    bg_h, bg_w = background.shape[:2]
    icon_h, icon_w = icon.size

    # 确保不越界
    x = max(0, min(x, bg_w - icon_w))
    y = max(0, min(y, bg_h - icon_h))

    # 转换为numpy数组
    icon_np = np.array(icon)

    # 处理透明通道
    if icon_np.shape[2] == 4:
        alpha = icon_np[:, :, 3:4].astype(np.float32) / 255.0
        icon_rgb = icon_np[:, :, :3].astype(np.float32)

        # 混合
        bg_roi = background[y:y+icon_h, x:x+icon_w].astype(np.float32)
        blended = bg_roi * (1 - alpha) + icon_rgb * alpha
        background[y:y+icon_h, x:x+icon_w] = blended.astype(np.uint8)
    else:
        background[y:y+icon_h, x:x+icon_w] = np.array(icon)

    return x, y, icon_w, icon_h


def generate_training_samples():
    """生成训练样本"""
    # 目录设置
    base_dir = Path("d:/project/rank_detector")
    source_dir = base_dir / "training_data"
    output_dir = base_dir / "dataset"

    # 创建输出目录
    for split in ["train", "val", "test"]:
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    # 扫描所有图标文件
    icon_files = list(source_dir.glob("*.png"))
    print(f"找到 {len(icon_files)} 个图标文件")

    # 按类别分组
    class_icons = defaultdict(list)
    for icon_file in icon_files:
        # 解析文件名: Bronze_1.png, Bronze_3_1.png
        parts = icon_file.stem.split("_")
        if len(parts) >= 2:
            rank = parts[0]
            try:
                level = int(parts[1])
                class_id = get_class_id(rank, level)
                class_icons[class_id].append(icon_file)
            except ValueError:
                print(f"Warning: 无法解析文件名 {icon_file.name}")
                continue

    print(f"\n类别分布:")
    for class_id in sorted(class_icons.keys()):
        print(f"  类别 {class_id} ({CLASS_NAMES[class_id]}): {len(class_icons[class_id])} 个文件")

    # 生成样本
    all_samples = []
    sample_id = 0

    for class_id, icons in class_icons.items():
        for _ in range(CONFIG["images_per_class"]):
            # 随机选择该类别的一个图标
            icon_path = random.choice(icons)
            icon_img = cv2.imread(str(icon_path), cv2.IMREAD_UNCHANGED)

            if icon_img is None:
                print(f"Warning: 无法读取 {icon_path}")
                continue

            # 创建随机背景
            canvas_h, canvas_w = CONFIG["canvas_size"][1], CONFIG["canvas_size"][0]
            background = create_random_background(canvas_w, canvas_h)

            # 调整图标大小
            icon_resized = cv2.resize(icon_img, CONFIG["icon_size"], interpolation=cv2.INTER_AREA)

            # 数据增强
            icon_augmented = augment_icon(icon_resized)

            # 随机位置粘贴
            max_x = canvas_w - CONFIG["icon_size"][0]
            max_y = canvas_h - CONFIG["icon_size"][1]
            x = random.randint(0, max_x)
            y = random.randint(0, max_y)

            x, y, w, h = paste_icon_with_alpha(background, icon_augmented, x, y)

            # 计算YOLO格式的标注（归一化坐标）
            x_center = (x + w / 2) / canvas_w
            y_center = (y + h / 2) / canvas_h
            width = w / canvas_w
            height = h / canvas_h

            # 保存样本信息
            all_samples.append({
                "image": background,
                "label": [class_id, x_center, y_center, width, height],
                "class_id": class_id
            })

            sample_id += 1
            if sample_id % 100 == 0:
                print(f"  已生成 {sample_id} 个样本...")

    print(f"\n总共生成 {len(all_samples)} 个样本")

    # 打乱并划分数据集
    random.shuffle(all_samples)

    total = len(all_samples)
    train_end = int(total * CONFIG["train_ratio"])
    val_end = train_end + int(total * CONFIG["val_ratio"])

    splits = {
        "train": all_samples[:train_end],
        "val": all_samples[train_end:val_end],
        "test": all_samples[val_end:]
    }

    # 保存数据集
    for split_name, samples in splits.items():
        print(f"\n保存 {split_name} 集 ({len(samples)} 个样本)...")

        for idx, sample in enumerate(samples):
            # 保存图片
            img_filename = f"{split_name}_{idx:06d}.jpg"
            img_path = output_dir / "images" / split_name / img_filename
            cv2.imwrite(str(img_path), sample["image"], [cv2.IMWRITE_JPEG_QUALITY, 95])

            # 保存标注
            label_filename = f"{split_name}_{idx:06d}.txt"
            label_path = output_dir / "labels" / split_name / label_filename
            with open(label_path, "w") as f:
                class_id, x, y, w, h = sample["label"]
                f.write(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")

    # 保存数据集配置
    dataset_config = {
        "classes": CLASS_NAMES,
        "nc": len(CLASS_NAMES),
        "splits": {
            "train": len(splits["train"]),
            "val": len(splits["val"]),
            "test": len(splits["test"])
        }
    }

    with open(output_dir / "data.yaml", "w", encoding="utf-8") as f:
        f.write(f"path: {output_dir.absolute()}\n")
        f.write(f"train: images/train\n")
        f.write(f"val: images/val\n")
        f.write(f"test: images/test\n\n")
        f.write(f"nc: {len(CLASS_NAMES)}\n")
        f.write(f"names: {CLASS_NAMES}\n")

    print(f"\n数据集配置已保存到 {output_dir / 'data.yaml'}")

    return output_dir


if __name__ == "__main__":
    print("开始生成训练数据...")
    print("=" * 50)

    output_dir = generate_training_samples()

    print("=" * 50)
    print(f"\n完成！数据集已保存到: {output_dir}")
    print("\n目录结构:")
    print(f"  {output_dir}/")
    print(f"    ├── images/")
    print(f"    │   ├── train/")
    print(f"    │   ├── val/")
    print(f"    │   └── test/")
    print(f"    ├── labels/")
    print(f"    │   ├── train/")
    print(f"    │   ├── val/")
    print(f"    │   └── test/")
    print(f"    └── data.yaml")
