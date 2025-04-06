from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
import mysql.connector
import bcrypt
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision import transforms
import os
import tempfile
from flask import render_template  # 导入 render_template

# 初始化 Flask 应用
app = Flask(__name__, static_folder='static')

# 设置一个密钥用于加密会话数据
app.secret_key = '123456'


# 数据库连接
def create_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='123456liu',
        database='citrus_system'
    )


# 用户登录
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode(), user['password'].encode()):
        session['user_id'] = user['id']  # 存储 user_id 到会话
        session['username'] = username  # 可选：存储 username
        return jsonify({'status': 'success', 'message': f'欢迎，{username}！'})
    else:
        return jsonify({'status': 'fail', 'message': '用户名或密码错误。'}), 401


# 用户注册
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = create_connection()
    cursor = conn.cursor()
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        return jsonify({'status': 'success', 'message': '注册成功！'})
    except mysql.connector.IntegrityError:
        return jsonify({'status': 'fail', 'message': '用户名已存在。'})
    finally:
        conn.close()


# 详细信息，根据当前用户查询图片信息
@app.route('/info')
def info():
    user_id = session.get('user_id')
    if not user_id:
        # 用户未登录，重定向到登录页面
        return redirect(url_for('login'))

    # 连接到数据库
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    # 查询 uploaded_images 表中当前用户的数据
    query = "SELECT upload_time, image_path FROM uploaded_images WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    images = cursor.fetchall()

    # 关闭数据库连接
    cursor.close()
    conn.close()

    # 将数据传递给模板
    return render_template('info.html', images=images)


# 首页路由，返回 index.html
@app.route('/')
def index():
    return render_template('index.html')  # 自动从 templates 文件夹中加载 index.html

# 自定义图片存储目录（服务器上的真实路径）
IMAGE_UPLOAD_DIR = 'static/images' #保存图片的路径

# 确保图片存储目录存在
os.makedirs(IMAGE_UPLOAD_DIR, exist_ok=True)

# 插入图片信息到数据库
def save_to_database(user_id, image_path):
    try:
        # print(user_id)
        connection = create_connection()
        cursor = connection.cursor()
        upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 获取当前时间
        query = "INSERT INTO uploaded_images (user_id, image_path, upload_time) VALUES (%s, %s, %s)"
        values = (user_id, image_path, upload_time)
        cursor.execute(query, values)
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# 多张图片识别路由
@app.route('/recognize_multiple', methods=['POST'])
def recognize_multiple():
    files = request.files.getlist('image')  # 获取上传的所有图片
    user_id = session.get('user_id')
    recognition_type = request.form.get('type')

    # 获取 BiShe 根目录
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    model_path = os.path.join(base_path, "checkpoint")
    npy_path = os.path.join(base_path, "code", "npy")

    # 定义柑橘果实和叶片的标签映射
    fruit_label_map = {
        "blackspot": "黑斑病",
        "canker": "溃疡病",
        "greening": "黄龙病",
        "scab": "疤痕病",
        "melanose": "黑点病",
        "healthy": "健康"
    }

    leaf_label_map = {
        "Blackspot": "黑斑病",
        "Canker": "溃疡病",
        "Greening": "黄龙病",
        "Melanose": "黑点病",
        "Healthy": "健康"
    }

    # 根据识别类型选择模型、标签文件和标签映射
    if recognition_type == "fruit":
        model_file = os.path.join(model_path, 'best-0.954fruit.pth')
        label_file = os.path.join(npy_path, 'idx_to_labels_fruit.npy')
        label_map = fruit_label_map
    else:
        model_file = os.path.join(model_path, 'best-0.916leaf.pth')
        label_file = os.path.join(npy_path, 'idx_to_labels_leaf.npy')
        label_map = leaf_label_map

    # 加载标签映射
    idx_to_labels = np.load(label_file, allow_pickle=True).item()

    # 设备选择
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    model = torch.load(model_file, map_location=device, weights_only=False)
    model.eval().to(device)

    # 图片预处理
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    results = []  # 用于存储所有图片的识别结果

    for file in files:
        # 为每个文件生成唯一的文件名
        file_extension = file.filename.split('.')[-1]  # 获取文件扩展名
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{file_extension}"
        image_path = os.path.join(IMAGE_UPLOAD_DIR, unique_filename)  # 服务器上的真实路径

        # 保存文件到服务器的真实路径
        file.save(image_path)

        img_pil = Image.open(image_path)  # 使用保存的文件路径
        input_img = transform(img_pil).unsqueeze(0).to(device)
        pred_logits = model(input_img)
        pred_softmax = F.softmax(pred_logits, dim=1)
        pred_id = torch.argmax(pred_softmax, dim=1).item()
        confidence = pred_softmax[0, pred_id].item()

        # 修正标签获取逻辑
        label_en = idx_to_labels.get(str(pred_id)) or idx_to_labels.get(pred_id, "Unknown Class")
        label_en = label_en.strip().lower()
        label_cn = label_map.get(label_en, "未知类别")

        # 逻辑判断映射英文到中文
        if label_en == "blackspot":
            label_cn = "黑斑病"
        elif label_en == "canker":
            label_cn = "溃疡病"
        elif label_en == "greening":
            label_cn = "黄龙病"
        elif label_en == "scab":
            label_cn = "疤痕病"
        elif label_en == "melanose":
            label_cn = "黑点病"
        elif label_en == "healthy":
            label_cn = "健康"
        else:
            label_cn = "未知类别"

        # 将图片信息存储到数据库
        save_to_database(user_id, image_path)

        # 保存当前图片的识别结果
        results.append({
            'image_name': unique_filename,
            'image_path': image_path,  # 服务器上的真实路径
            'label_cn': label_cn,
            'label_en': label_en,
            'confidence': f"{confidence * 100:.2f}%",
            'treatment': "治疗方法待定"
        })

    return jsonify({'results': results})

# 用户注销
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)  # 清除会话中的 user_id
    session.pop('username', None)  # 可选：清除 username
    return jsonify({'status': 'success', 'message': '已注销。'})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
# wandb login --relogin
# e763a42c596154fa12254692f37493033119d77e
