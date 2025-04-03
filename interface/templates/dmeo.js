// 切换表单显示
function toggleForm(formType) {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    if (formType === 'login') {
        loginForm.classList.add('active');
        registerForm.classList.remove('active');
    } else {
        registerForm.classList.add('active');
        loginForm.classList.remove('active');
    }
}

// 登录逻辑
function login() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    fetch('/login', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username, password})
    })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            if (data.status === 'success') {
                document.getElementById('auth-container').style.display = 'none';
                document.getElementById('recognition').style.display = 'block';
            }
        });
}

// 注册逻辑
function register() {
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;

    fetch('/register', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username, password})
    })
        .then(response => response.json())
        .then(data => alert(data.message));
}

let uploadedImages = [];
let imageContainers = [];

function previewImages() {
    const files = document.getElementById('image-upload').files;
    const resultContainer = document.getElementById('result');
    uploadedImages = [];
    imageContainers = [];
    resultContainer.innerHTML = "";

    let filePromises = [];

    for (let i = 0; i < files.length; i++) {
        const reader = new FileReader();

        let filePromise = new Promise((resolve, reject) => {
            reader.onload = function (event) {
                const imgElement = document.createElement('img');
                imgElement.src = event.target.result;
                imgElement.alt = '上传的图片';

                uploadedImages.push({file: files[i], src: event.target.result, index: i});

                const imageContainer = document.createElement('div');
                imageContainer.classList.add('image-container');
                imageContainer.innerHTML = `<h3>图片 ${i + 1}</h3>`;
                imageContainer.appendChild(imgElement);

                imageContainers[i] = imageContainer;
                resolve();
            };

            reader.onerror = function () {
                reject('图片读取失败');
            };

            reader.readAsDataURL(files[i]);
        });

        filePromises.push(filePromise);
    }

    Promise.all(filePromises).then(() => {
        imageContainers.forEach(container => {
            resultContainer.appendChild(container);
        });
    }).catch((error) => {
        console.error(error);
    });
}

//识别
// 全局变量用于存储上传的图片信息
let uploadedImageInfos = [];

// 上传图片并获取信息的函数
async function uploadImages(formData) {
    try {
        const response = await fetch('/upload_multiple_images', {
            method: 'POST', body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            uploadedImageInfos = data.uploaded_images; // 存储上传的图片信息
            console.log('上传成功:', uploadedImageInfos);
            return true;
        } else {
            alert('上传失败: ' + data.message);
            return false;
        }
    } catch (error) {
        console.error('上传过程中发生错误:', error);
        alert('上传过程中发生错误: ' + error.message);
        return false;
    }
}

// 识别函数
async function recognize() {
    const formData = new FormData();
    const files = document.getElementById('image-upload').files;
    const type = document.getElementById('recognition-type').value;

    // 获取结果容器
    const resultContainer = document.getElementById('result');

    // 获取进度条容器
    const progressBar = document.getElementById('progress-bar');
    const progressInner = document.querySelector('#progress-bar .progress');

    // 清空之前的识别结果和图片容器
    resultContainer.innerHTML = "";
    uploadedImages = []; // 清空上传的图片记录
    imageContainers = []; // 清空图片容器数组

    // 如果没有文件，提示用户上传图片
    if (files.length === 0) {
        alert("请先上传图片！");
        return;
    }

    // 将文件添加到 FormData
    for (let i = 0; i < files.length; i++) {
        formData.append('images', files[i]); // 修改为 'images' 以支持多文件上传
    }
    formData.append('type', type);

    // 显示进度条
    progressBar.style.display = "block";

    // 上传图片并获取信息
    const uploadSuccess = await uploadImages(formData);
    if (!uploadSuccess) {
        // 隐藏进度条
        if (progressBar) {
            progressBar.style.display = "none";
        }
        return;
    }

    // 模拟进度更新（可根据实际需求调整）
    let progress = 50; // 假设上传占50%，识别占50%
    progressInner.style.width = progress + "%";

    // 等待一段时间模拟识别过程（实际应用中应调用实际的识别API）
    await new Promise(resolve => setTimeout(resolve, 1000));

    // 更新进度到100%
    progressInner.style.width = "100%";

    // 这里可以调用实际的识别API，并将结果展示在resultContainer中

    // 示例：假设识别成功，显示上传的图片信息
    resultContainer.innerHTML = "<h3>识别结果：</h3>";
    uploadedImageInfos.forEach(image => {
        const div = document.createElement('div');
        div.innerHTML = `
            <p></p>
            <!-- 你可以在这里添加更多展示信息，例如显示图片 -->
        `;
        resultContainer.appendChild(div);
    });

    // 隐藏进度条
    if (progressBar) {
        progressBar.style.display = "none";
    }
}

// 发送识别请求
function sendRecognitionRequest(formData, resultContainer, progressBar, progressInner) {
    fetch('/recognize_multiple', {
        method: 'POST', body: formData
    })
        .then(response => response.json())
        .then(data => {
            // 遍历识别结果并显示
            data.results.forEach((result, index) => {
                // 创建图片容器
                const imageContainer = document.createElement('div');
                imageContainer.classList.add('image-container');

                // 创建图片元素
                const imgElement = document.createElement('img');
                imgElement.src = uploadedImages[index]?.src || ''; // 使用上传的图片 URL
                imgElement.alt = `图片 ${index + 1}`;
                imgElement.style.maxWidth = '200px'; // 设置图片最大宽度
                imgElement.style.margin = '10px 0'; // 设置图片间距

                // 创建识别结果的 HTML
                let diseaseLink = '';
                switch (result.label_en) {
                    case 'blackspot':
                        diseaseLink = './static/blackspot.html';
                        break;
                    case 'greening':
                        diseaseLink = './static/greening.html';
                        break;
                    case 'scab':
                        diseaseLink = './static/scab.html';
                        break;
                    case 'canker':
                        diseaseLink = './static/canker.html';
                        break;
                    case 'melanose':
                        diseaseLink = './static/melanose.html';
                        break;
                    case 'healthy':
                        diseaseLink = './static/healthy.html';
                        break;
                    default:
                        diseaseLink = '#';
                        break;
                }

                const resultText = `
                    <h3>图片 ${index + 1} 识别结果</h3>
                     <p>类别: ${result.label_cn} (${result.label_en})</p>
                    <p>置信度: ${result.confidence}</p>
                    <p><a href="${result.disease_link}" target="_blank">查看解决办法</a></p>
                `;


                // 将图片和识别结果添加到图片容器
                imageContainer.appendChild(imgElement);
                imageContainer.innerHTML += resultText; // 拼接识别结果

                // 将图片容器添加到结果区域
                resultContainer.appendChild(imageContainer);

                // 保存图片容器到数组
                imageContainers.push(imageContainer);
            });

            // 隐藏进度条
            if (progressBar) {
                progressBar.style.display = "none";
            }
        })
        .catch(err => {
            console.error('请求失败:', err);

            // 隐藏进度条
            if (progressBar) {
                progressBar.style.display = "none";
            }
        });
}

function goToInfo() {
    window.location.href = "/info";
}