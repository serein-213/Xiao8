import os
from flask import Flask, render_template, jsonify, request
from utils.preferences import load_user_preferences, update_user_preferences, validate_preferences

# 初始化Flask应用
app = Flask(__name__)

# 修改点：将扫描的根目录直接设置为 'static' 文件夹
SEARCH_ROOT_DIR = app.static_folder or 'static'

def find_models():
    """
    递归扫描整个 'static' 文件夹，查找所有包含 '.model3.json' 文件的子目录。
    """
    found_models = []
    if not os.path.exists(SEARCH_ROOT_DIR):
        print(f"警告：指定的静态文件夹路径不存在: {SEARCH_ROOT_DIR}")
        return []

    # os.walk会遍历指定的根目录下的所有文件夹和文件
    for root, dirs, files in os.walk(SEARCH_ROOT_DIR):
        for file in files:
            if file.endswith('.model3.json'):
                # 获取模型名称 (使用其所在的文件夹名，更加直观)
                model_name = os.path.basename(root)
                
                # 构建可被浏览器访问的URL路径
                # 1. 计算文件相对于 static_folder 的路径
                relative_path = os.path.relpath(os.path.join(root, file), app.static_folder)
                # 2. 将本地路径分隔符 (如'\') 替换为URL分隔符 ('/')
                model_path = relative_path.replace(os.path.sep, '/')
                
                found_models.append({
                    "name": model_name,
                    "path": f"/static/{model_path}"
                })
                
                # 优化：一旦在某个目录找到模型json，就无需再继续深入该目录的子目录
                dirs[:] = []
                break
                
    return found_models

@app.route('/')
def l2d_manager():
    """渲染主控制页面"""
    return render_template('l2d_manager.html')

@app.route('/api/models')
def get_models():
    """
    API接口，调用扫描函数并以JSON格式返回找到的模型列表。
    """
    models = find_models()
    return jsonify(models)

@app.route('/api/preferences', methods=['GET'])
def get_preferences():
    """获取用户偏好设置"""
    preferences = load_user_preferences()
    return jsonify(preferences)

@app.route('/api/preferences', methods=['POST'])
def save_preferences():
    """保存用户偏好设置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "无效的数据"}), 400
        
        # 验证偏好数据
        if not validate_preferences(data):
            return jsonify({"success": False, "error": "偏好数据格式无效"}), 400
        
        # 更新偏好
        if update_user_preferences(data):
            return jsonify({"success": True, "message": "偏好设置已保存"})
        else:
            return jsonify({"success": False, "error": "保存失败"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)