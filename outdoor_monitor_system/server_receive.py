#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask 服务器 - 接收监控设备上传的文件
提供图片访问和简单的 Web 界面
"""

from flask import Flask, request, jsonify, send_from_directory, render_template_string
from pathlib import Path
import time
import os

app = Flask(__name__)

# 配置
BASE_DIR = Path("./uploads")
BASE_DIR.mkdir(exist_ok=True)
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)


# ============ HTML 模板 ============

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>监控系统 - 文件浏览</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .upload-form { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .file-list { background: white; padding: 20px; border-radius: 8px; }
        .file-item { padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }
        .file-item:last-child { border-bottom: none; }
        .file-item img { max-width: 200px; max-height: 150px; }
        .alert { padding: 15px; margin-bottom: 20px; border-radius: 5px; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>📹 监控系统 - 文件服务器</h1>

    <div class="upload-form">
        <h2>文件上传</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <input type="text" name="device_id" placeholder="设备ID" value="VF2-01">
            <input type="text" name="kind" placeholder="类型 (snapshot/event)" value="event">
            <button type="submit">上传</button>
        </form>
    </div>

    <div class="file-list">
        <h2>最近文件</h2>
        {% if files %}
            {% for f in files %}
            <div class="file-item">
                <span>{{ f.name }} ({{ f.time }})</span>
                <span>{{ f.kind }}</span>
                {% if f.is_image %}
                <a href="/uploads/{{ f.name }}">查看</a>
                {% endif %}
            </div>
            {% endfor %}
        {% else %}
            <p>暂无文件</p>
        {% endif %}
    </div>
</body>
</html>
"""


# ============ 路由 ============

@app.route("/")
def index():
    """首页"""
    files = []
    for f in sorted(BASE_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
        if f.is_file():
            files.append({
                'name': f.name,
                'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(f.stat().st_mtime)),
                'kind': 'image' if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif'] else 'video',
                'is_image': f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']
            })

    return render_template_string(INDEX_HTML, files=files)


@app.route("/upload", methods=["POST"])
def upload():
    """
    接收文件上传
    """
    try:
        if 'file' not in request.files:
            return jsonify({'ok': False, 'error': '没有文件'}), 400

        file = request.files['file']
        device_id = request.form.get('device_id', 'unknown')
        kind = request.form.get('kind', 'unknown')

        if file.filename == '':
            return jsonify({'ok': False, 'error': '文件名为空'}), 400

        # 生成文件名
        timestamp = int(time.time())
        ext = Path(file.filename).suffix.lower()
        new_filename = f"{timestamp}_{device_id}_{kind}{ext}"
        filepath = BASE_DIR / new_filename

        # 保存文件
        file.save(filepath)

        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 上传: {new_filename} (设备: {device_id}, 类型: {kind})")

        return jsonify({
            'ok': True,
            'path': str(filepath),
            'url': f"/uploads/{new_filename}",
            'filename': new_filename
        })

    except Exception as e:
        print(f"上传错误: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    """访问上传的文件"""
    return send_from_directory(BASE_DIR, filename)


@app.route("/api/status")
def status():
    """服务器状态"""
    return jsonify({
        'ok': True,
        'uptime': time.time() - app.start_time,
        'files_count': len(list(BASE_DIR.iterdir())),
        'storage_used': sum(f.stat().st_size for f in BASE_DIR.iterdir() if f.is_file())
    })


@app.route("/health")
def health():
    """健康检查"""
    return "OK"


# ============ 启动 ============

if __name__ == "__main__":
    print("""
========================================
  监控系统 - Flask 文件服务器
========================================
  上传地址: http://your-server-ip:5000/upload
  Web界面:  http://your-server-ip:5000/
========================================
    """)

    app.start_time = time.time()
    app.run(host="0.0.0.0", port=5000, debug=False)
