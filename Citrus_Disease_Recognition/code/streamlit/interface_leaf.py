import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
import streamlit as st
from torchvision import transforms

# 加载标签字典和模型
idx_to_labels = np.load('../npy/idx_to_labels_leaf.npy', allow_pickle=True).item()
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

model = torch.load('../../checkpoint/best-0.916leaf.pth', map_location=device)
model = model.eval().to(device)

# 测试集图像预处理
test_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# 创建 Streamlit 页面
st.title('柑橘叶疾病识别系统')

# 上传图片
uploaded_file = st.file_uploader("上传一张柑橘叶图片进行识别", type=["jpg", "png", "jpeg"])

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
    elif label_en == "melanose":
        label_cn = "黑点病"
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
streamlit run interface_leaf.py
"""