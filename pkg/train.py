"""
YOLOv8 训练脚本
用于训练图标检测模型
"""
import os
from pathlib import Path
from ultralytics import YOLO

# 配置
CONFIG = {
    # 数据集路径
    "data": "d:/project/rank_detector/dataset/data.yaml",

    # 模型选择: yolov8n.yaml (nano), yolov8s.yaml (small), yolov8m.yaml (medium)
    "model": "yolov8n.yaml",  # 从配置文件创建，不下载预训练权重

    # 训练轮数
    "epochs": 100,

    # 图像尺寸
    "imgsz": 640,

    # 批次大小 (GPU可以设置更大)
    "batch": 32,  # GPU训练增大batch size

    # 设备: 0=GPU, cpu=CPU
    "device": "0",  # 使用GPU训练

    # 工作进程数
    "workers": 8,

    # 输出目录
    "project": "d:/project/rank_detector/runs",
    "name": "rank_detector",
}


def train_model():
    """训练 YOLOv8 模型"""
    print("=" * 50)
    print("开始训练 YOLOv8 图标检测模型")
    print("=" * 50)

    # 创建输出目录
    Path(CONFIG["project"]).mkdir(parents=True, exist_ok=True)

    # 加载或创建模型
    print(f"\n创建模型: {CONFIG['model']}")

    # 从配置文件创建模型并指定类别数
    model = YOLO(CONFIG["model"])
    model.nc = 21  # 设置类别数为21 (20个等级类 + 1个Legendary类)

    print(f"模型类别数: 21")

    # 训练配置
    train_args = {
        "data": CONFIG["data"],
        "epochs": CONFIG["epochs"],
        "imgsz": CONFIG["imgsz"],
        "batch": CONFIG["batch"],
        "device": CONFIG["device"],
        "workers": CONFIG["workers"],
        "project": CONFIG["project"],
        "name": CONFIG["name"],
        "verbose": True,
        "plots": True,
        "save": True,
        "patience": 20,  # 早停：20轮无改善则停止
        "save_period": 10,  # 每10轮保存一次
        "amp": False,  # 禁用AMP检查，避免下载预训练权重
    }

    print("\n训练配置:")
    for key, value in train_args.items():
        print(f"  {key}: {value}")

    # 开始训练
    print("\n开始训练...")
    print("-" * 50)

    results = model.train(**train_args)

    print("-" * 50)
    print("\n训练完成!")

    # 返回最佳模型路径
    best_model_path = Path(CONFIG["project"]) / CONFIG["name"] / "weights" / "best.pt"
    print(f"\n最佳模型已保存到: {best_model_path}")

    return best_model_path


def validate_model(model_path):
    """验证模型性能"""
    print("\n" + "=" * 50)
    print("验证模型性能")
    print("=" * 50)

    # 加载最佳模型
    model = YOLO(model_path)

    # 在验证集上评估
    metrics = model.val(
        data=CONFIG["data"],
        split="val",
        device=CONFIG["device"]
    )

    print("\n验证结果:")
    print(f"  mAP50: {metrics.box.map50:.4f}")
    print(f"  mAP50-95: {metrics.box.map:.4f}")
    print(f"  Precision: {metrics.box.mp:.4f}")
    print(f"  Recall: {metrics.box.mr:.4f}")

    return metrics


if __name__ == "__main__":
    # 训练模型
    best_model = train_model()

    # 验证模型
    validate_model(best_model)

    print("\n" + "=" * 50)
    print("全部完成!")
    print("=" * 50)
