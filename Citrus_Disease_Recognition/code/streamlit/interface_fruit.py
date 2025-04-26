import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
import streamlit as st
from torchvision import transforms

# 加载标签字典和模型
idx_to_labels = np.load('../npy/idx_to_labels_fruit.npy', allow_pickle=True).item()
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

model = torch.load('../../checkpoint/best-0.954fruit.pth', map_location=device)
model = model.eval().to(device)

# 测试集图像预处理
test_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# 创建 Streamlit 页面
st.title('柑橘果实疾病识别系统')

# 上传图片
uploaded_file = st.file_uploader("上传一张柑橘果实图片进行识别", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    # 创建两列布局
    col1, col2 = st.columns([1, 1])

    with col1:
        img_pil = Image.open(uploaded_file)
        st.image(img_pil, caption="上传的图片", width=300)

    # 预处理图片
    input_img = test_transform(img_pil)
    input_img = input_img.unsqueeze(0).to(device)

    # 预测
    pred_logits = model(input_img)
    pred_softmax = F.softmax(pred_logits, dim=1)

    # 获取 Top 1 结果
    top1 = torch.topk(pred_softmax, 1)
    pred_id = top1[1].cpu().detach().item()
    confidence = top1[0].cpu().detach().item()

    # 获取模型返回的英文类别
    label_en = idx_to_labels.get(str(pred_id)) or idx_to_labels.get(pred_id, "Unknown Class")

    # 格式化 label_en（去空格，大小写归一化）
    label_en = label_en.strip().lower()

    # 逻辑判断映射英文到中文
    if label_en == "blackspot":
        label_cn = "黑斑病"
    elif label_en == "canker":
        label_cn = "溃疡病"
    elif label_en == "greening":
        label_cn = "黄龙病"
    elif label_en == "scab":
        label_cn = "疤痕病"
    elif label_en == "healthy":
        label_cn = "健康"
    else:
        label_cn = "未知类别"

    # 右侧显示结果
    with col2:
        st.subheader("预测结果")
        st.write(f"**类别:** {label_cn} ({label_en})")
        st.write(f"**置信度:** {confidence*100:.2f}%")
"""
cd /Users/liubaozhang/PycharmProjects/pythonProject/BiShe/code/
streamlit run interface_fruit.py
"""

"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
from torch.utils.data import DataLoader
from torchvision import models, transforms
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import numpy as np
from tqdm import tqdm
import os

# 数据增强（增强模型泛化能力）
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(30),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
    transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.8, 1.2)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# 测试集图像预处理
test_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# 加载预训练模型 ResNet50
model = models.resnet50(pretrained=True)

# 解冻部分层进行微调
for name, param in model.named_parameters():
    if "layer4" in name or "fc" in name:
        param.requires_grad = True  # 只微调最后的残差块和全连接层
    else:
        param.requires_grad = False

# 修改全连接层
n_class = 5  # 替换为你数据集的实际类别数
model.fc = nn.Sequential(
    nn.Dropout(0.5),  # 增加 Dropout 减少过拟合
    nn.Linear(model.fc.in_features, n_class)
)

# 训练配置
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-4, weight_decay=1e-4)
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)  # 加入 label smoothing

# 学习率调度器
scheduler = lr_scheduler.CosineAnnealingLR(optimizer, T_max=10)

# 数据加载器
BATCH_SIZE = 32
train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=4)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=4)

# 训练与评估
def train_one_epoch(epoch):
    model.train()
    total_loss = 0
    all_preds, all_labels = [], []
    
    for images, labels in tqdm(train_loader):
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()

        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        preds = outputs.argmax(dim=1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

    accuracy = accuracy_score(all_labels, all_preds)
    print(f"Epoch {epoch}, Loss: {total_loss/len(train_loader):.4f}, Accuracy: {accuracy:.4f}")


def evaluate():
    model.eval()
    all_preds, all_labels = [], []
    
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            preds = outputs.argmax(dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    accuracy = accuracy_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds, average='macro')
    recall = recall_score(all_labels, all_preds, average='macro')
    f1 = f1_score(all_labels, all_preds, average='macro')

    print(f"Test Accuracy: {accuracy:.4f}, Precision: {precision:.4f}, Recall: {recall:.4f}, F1 Score: {f1:.4f}")


# 训练循环
best_accuracy = 0
EPOCHS = 30

for epoch in range(1, EPOCHS + 1):
    train_one_epoch(epoch)
    scheduler.step()
    
    # 测试集评估
    evaluate()
    
    # 模型保存
    current_accuracy = accuracy_score(all_labels, all_preds)
    if current_accuracy > best_accuracy:
        best_accuracy = current_accuracy
        torch.save(model.state_dict(), f'checkpoint/best_model_{best_accuracy:.4f}.pth')
        print(f"保存新的最佳模型，准确率: {best_accuracy:.4f}")

"""