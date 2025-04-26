import streamlit as st
import mysql.connector
import bcrypt
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision import transforms
import os


# 数据库连接
def create_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='123456liu',
        database='citrus_system'
    )


# 用户验证
def authenticate(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return bcrypt.checkpw(password.encode(), result[0].encode())
    return False


# 注册用户
def register_user(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        st.success("注册成功！")
    except mysql.connector.IntegrityError:
        st.error("用户名已存在。")
    finally:
        conn.close()


# 识别系统
def disease_recognition():
    st.title("🍊 柑橘疾病识别系统")

    # 使用复选框选择识别类型
    options = st.multiselect("请选择识别类型", ["柑橘果实疾病识别", "柑橘叶疾病识别"])

    base_path = os.path.dirname(__file__)
    model_path = os.path.join(base_path, "../../checkpoint")
    npy_path = os.path.join(base_path, "../npy")

    # 设置模型和标签
    model_file = None
    label_file = None
    label_map = {}

    if "柑橘果实疾病识别" in options:
        model_file = os.path.join(model_path, 'best-0.954fruit.pth')
        label_file = os.path.join(npy_path, 'idx_to_labels_fruit.npy')
        label_map.update({
            "blackspot": "黑斑病",
            "canker": "溃疡病",
            "greening": "黄龙病",
            "scab": "疤痕病",
            "melanose": "黑点病",
            "healthy": "健康"
        })

    if "柑橘叶疾病识别" in options:
        model_file = os.path.join(model_path, 'best-0.916leaf.pth')
        label_file = os.path.join(npy_path, 'idx_to_labels_leaf.npy')
        label_map.update({
            "blackspot": "黑斑病",
            "canker": "溃疡病",
            "greening": "黄龙病",
            "melanose": "黑点病",
            "healthy": "健康"
        })

    if not model_file:
        st.warning("请选择至少一种疾病类型！")
        return

    idx_to_labels = np.load(label_file, allow_pickle=True).item()
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    model = torch.load(model_file, map_location=device)
    model.eval().to(device)

    # 图片上传
    uploaded_file = st.file_uploader("上传一张图片进行识别", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        img_pil = Image.open(uploaded_file)
        st.image(img_pil, caption="上传的图片", width=300)

        transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        input_img = transform(img_pil).unsqueeze(0).to(device)
        pred_logits = model(input_img)
        pred_softmax = F.softmax(pred_logits, dim=1)
        top1 = torch.topk(pred_softmax, 1)
        pred_id = top1[1].cpu().detach().item()
        confidence = top1[0].cpu().detach().item()

        # 修正标签获取逻辑
        label_en = idx_to_labels.get(str(pred_id)) or idx_to_labels.get(pred_id, "Unknown Class")
        label_en = label_en.strip().lower()
        label_cn = label_map.get(label_en, "未知类别")

        st.subheader("识别结果")
        st.write(f"**类别:** {label_cn} ({label_en})")
        st.write(f"**置信度:** {confidence * 100:.2f}%")


# 页面切换逻辑
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'page' not in st.session_state:
    st.session_state.page = 'login'

if st.session_state.page == 'login' and not st.session_state.logged_in:
    # 登录界面
    st.title("🔐 柑橘疾病识别系统 - 登录")

    menu = st.sidebar.selectbox("选择操作", ["登录", "注册"])
    if menu == "登录":
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")

        if st.button("登录"):
            if authenticate(username, password):
                st.success(f"欢迎，{username}！")
                st.session_state.logged_in = True
                st.session_state.page = 'recognition'
            else:
                st.error("用户名或密码错误。")

    elif menu == "注册":
        new_username = st.text_input("新用户名")
        new_password = st.text_input("新密码", type="password")
        if st.button("注册"):
            if new_username and new_password:
                register_user(new_username, new_password)
            else:
                st.warning("请输入完整的用户名和密码。")

elif st.session_state.page == 'recognition' and st.session_state.logged_in:
    disease_recognition()
