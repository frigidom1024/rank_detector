import os
import shutil
from pathlib import Path
from collections import defaultdict

# 源目录和目标目录
source_dir = Path("d:/project/rank_detector/data")
target_dir = Path("d:/project/rank_detector/training_data")
target_dir.mkdir(exist_ok=True)

# 段位映射
rank_mapping = {
    "Bro": "Bronze",
    "Sli": "Silver",
    "Gold": "Gold",
    "Dia": "Diamond",
    "Leg": "Legendary"
}

# 存储每个段位-等级组合的文件
rank_level_files = defaultdict(list)

# 遍历所有段位目录
for rank_dir in source_dir.iterdir():
    if not rank_dir.is_dir():
        continue

    rank_name = rank_dir.name
    print(f"Processing {rank_name}...")

    # 遍历该段位下的所有文件
    for img_file in rank_dir.glob("*.png"):
        # 解析文件名获取等级
        filename = img_file.stem  # 不带扩展名的文件名
        ext = img_file.suffix

        # 尝试从文件名中提取等级数字
        level = None
        for char in filename:
            if char.isdigit():
                # 找数字
                digits = ''.join(c for c in filename if c.isdigit())
                if digits:
                    level = int(digits)
                break

        if level is None:
            # 如果找不到数字，跳过或使用默认值
            print(f"  Warning: Could not extract level from {filename}, using 1")
            level = 1

        # 构建新文件名基础
        rank_en = rank_mapping.get(rank_name, rank_name)
        base_name = f"{rank_en}_{level}"

        rank_level_files[(rank_en, level)].append((img_file, filename))

# 复制并重命名文件
copied_files = []
for (rank, level), files in sorted(rank_level_files.items()):
    if len(files) == 1:
        # 没有重复，直接复制
        src_file, orig_name = files[0]
        new_name = f"{rank}_{level}{src_file.suffix}"
        dest_file = target_dir / new_name
        shutil.copy2(src_file, dest_file)
        copied_files.append(new_name)
        print(f"  {orig_name} -> {new_name}")
    else:
        # 有多个变体，添加区别序号
        for idx, (src_file, orig_name) in enumerate(sorted(files), 1):
            new_name = f"{rank}_{level}_{idx}{src_file.suffix}"
            dest_file = target_dir / new_name
            shutil.copy2(src_file, dest_file)
            copied_files.append(new_name)
            print(f"  {orig_name} -> {new_name}")

print(f"\n总共复制了 {len(copied_files)} 个文件到 {target_dir}")

# 输出文件列表
print("\n整理后的文件列表:")
for f in sorted(copied_files):
    print(f"  {f}")
