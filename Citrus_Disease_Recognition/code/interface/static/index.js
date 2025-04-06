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
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
    })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            if (data.status === 'success') {
                // 登录成功，跳转到识别页面或隐藏登录表单
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
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
    })
        .then(response => response.json())
        .then(data => alert(data.message));
}

let uploadedImages = []; // 用来存储上传的图片和顺序
let imageContainers = []; // 用来存储每个图片的容器

function previewImages() {
    const files = document.getElementById('image-upload').files;
    const resultContainer = document.getElementById('result');
    uploadedImages = [];  // 清空已上传的图片记录
    imageContainers = [];  // 清空之前的图片容器

    resultContainer.innerHTML = "";  // 清空之前的预览

    // 使用Promise来确保图片按顺序上传并预览
    let filePromises = [];

    // 显示所有上传的图片，并且按文件顺序展示
    for (let i = 0; i < files.length; i++) {
        const reader = new FileReader();

        let filePromise = new Promise((resolve, reject) => {
            reader.onload = function (event) {
                const imgElement = document.createElement('img');
                imgElement.src = event.target.result;
                imgElement.alt = '上传的图片';
                imgElement.style.maxWidth = '200px'; // 可根据需要调整大小

                // 保存上传的图片文件和其顺序
                uploadedImages.push({file: files[i], src: event.target.result, index: i});

                const imageContainer = document.createElement('div');
                imageContainer.classList.add('image-container');

                // 添加图片和标题
                imageContainer.innerHTML =
                    `<h3>图片 ${i + 1}</h3>`;
                imageContainer.appendChild(imgElement);

                // 将图片容器按顺序保存在数组中
                imageContainers[i] = imageContainer;

                resolve(); // 图片加载完成后执行
            };

            reader.onerror = function () {
                reject('图片读取失败');
            };

            reader.readAsDataURL(files[i]);
        });

        filePromises.push(filePromise); // 将每个文件的Promise放入数组
    }

    // 等待所有文件都加载完成后按顺序插入图片
    Promise.all(filePromises).then(() => {
        // 所有图片都加载完成后，按顺序插入
        imageContainers.forEach(container => {
            resultContainer.appendChild(container);
        });
    }).catch((error) => {
        console.error(error);
    });
}

function recognize() {
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
        formData.append('image', files[i]);
    }
    formData.append('type', type);

    // 显示进度条
    progressBar.style.display = "block";

    // 预览上传的图片
    const readerPromises = [];
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const reader = new FileReader();

        const promise = new Promise((resolve, reject) => {
            reader.onload = function (event) {
                // 保存图片的 URL
                uploadedImages.push({src: event.target.result, index: i});
                resolve();
            };
            reader.onerror = function () {
                reject(`图片 ${i + 1} 读取失败`);
            };
            reader.readAsDataURL(file); // 读取图片文件
        });

        readerPromises.push(promise);
    }

    // 等待所有图片加载完成后，再发送识别请求
    Promise.all(readerPromises)
        .then(() => {
            // 显示进度条动画
            let progress = 0;

            // 模拟进度更新
            const interval = setInterval(() => {
                progress += 50; // 每次增加 20%
                progressInner.style.width = progress + "%";

                // 如果进度达到 100%，停止更新并发送请求
                if (progress >= 100) {
                    clearInterval(interval);
                    sendRecognitionRequest(formData, resultContainer, progressBar, progressInner);
                }
            }, 500); // 每 500ms 更新一次进度
        })
        .catch(err => {
            console.error('图片加载失败:', err);

            // 隐藏进度条
            if (progressBar) {
                progressBar.style.display = "none";
            }
        });
}

// 发送识别请求
function sendRecognitionRequest(formData, resultContainer, progressBar, progressInner) {
    fetch('/recognize_multiple', {
        method: 'POST',
        body: formData
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
                <p><a href="${diseaseLink}" target="_blank">查看解决办法</a></p>
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
//跳转到详细信息页面
// 在当前页面打开详细信息页面
function goToInfo() {
    window.location.href = '/info';
}
/*
function goToInfo() {
    window.open('/info');
}*/
