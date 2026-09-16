from flask import Flask, jsonify, request
from datetime import datetime, timezone
import time

app = Flask(__name__)
port = 3000

start_time = time.time()


@app.before_request
def log_request():
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"{timestamp} {request.method} {request.path}")


@app.route('/', methods=['GET'])
def index():
    return 'Welcome to the server!'


@app.route('/api/time', methods=['GET'])
def get_time():
    return jsonify({
        'time': int(time.time() * 1000),
        'timeZone': 'UTC'
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        'status': 'OK',
        'uptime': time.time() - start_time
    })


@app.route('/api/info', methods=['GET'])
def get_info():
    return jsonify({
        'author': 'Mikhail',
        'version': '1.0'
    })


@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    return jsonify({
        'message': 'User information',
        'userId': user_id
    })


@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify({
        'users': ['User1', 'User2', 'User3', 'User4']
    })


@app.route('/api/roles', methods=['GET'])
def get_roles():
    return jsonify({
        'roles': ['Administrator', 'User', 'Designer']
    })


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify({
        'tasks': {
            'main': 'Build a project',
            'secondary': 'Fix errors',
            'optional': 'Make no mistakes'
        }
    })


@app.route('/api/projects', methods=['GET'])
def get_projects():
    return jsonify({
        'projects': {
            'Eirvale': {
                'id': 0,
                'description': 'Gamified kanban'
            },
            'Something': {
                'id': 1,
                'description': 'Something'
            }
        }
    })


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_by_id(task_id):
    return jsonify({
        'id': task_id,
        'task': 'Task 1'
    })


@app.errorhandler(404)
def not_found(e):
    return 'Not Found', 404


if __name__ == '__main__':
    print(f"Server URL: http://localhost:{port}")
    app.run(port=port)