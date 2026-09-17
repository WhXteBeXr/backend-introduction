import logging
from datetime import datetime

from flask import Flask, Response, jsonify, request

app = Flask(__name__)
port = 3001

logging.basicConfig(
    filename="server.log",
    level=logging.INFO,
    format="%(message)s",
)

tasks = [
    {"id": 0, "title": "Первая задача", "done": False, "priority": "high", "deadline": "2026-09-16"},
    {"id": 1, "title": "Вторая задача", "done": True, "priority": "low", "deadline": "2026-12-25"},
    {"id": 2, "title": "Третья задача", "done": False, "priority": "medium", "deadline": "2026-09-20"},
]

next_id = len(tasks)


def validate_task_data(data: dict, partial: bool = False) -> str | None:
    """Возвращает текст ошибки или None, если всё ок."""
    if not partial and "title" not in data:
        return "Title is required"

    if "title" in data and not isinstance(data["title"], str):
        return "Title must be a string"

    if "done" in data and not isinstance(data["done"], bool):
        return "Done must be a boolean"

    if "priority" in data and data["priority"] not in ("low", "medium", "high"):
        return "Priority must be one of ['low', 'medium', 'high']"

    return None


@app.before_request
def log_request() -> None:
    timestamp = datetime.now().isoformat()
    log_line = f"{timestamp} {request.method} {request.path}"
    print(log_line)
    logging.info(log_line)


@app.route("/", methods=["GET"])
def index() -> str:
    return "Welcome, that's my server!"


@app.route("/api/tasks", methods=["GET"])
def get_tasks() -> tuple[Response, int] | Response:
    result = tasks.copy()

    # Поиск по title
    search = request.args.get("search")
    if search:
        result = [t for t in result if search.lower() in t["title"].lower()]

    # Сортировка
    sort_field = request.args.get("sort")
    order = request.args.get("order", "asc")
    if sort_field:
        if sort_field not in ("id", "title", "priority", "deadline", "done"):
            return jsonify({"error": f"Can't sort by {sort_field}"}), 400
        reverse = order == "desc"
        result = sorted(result, key=lambda t: t.get(sort_field), reverse=reverse)

    # Пагинация
    page = request.args.get("page", type=int)
    limit = request.args.get("limit", type=int)
    if page is not None and limit is not None:
        if page < 1 or limit < 1:
            return jsonify({"error": "page and limit myst be positive int"}), 400
        start = (page - 1) * limit
        end = start + limit
        result = result[start:end]

    return jsonify({"count": len(result), "tasks": result})


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
def get_item(task_id: int) -> tuple[Response, int] | Response:
    item = next((task for task in tasks if task["id"] == task_id), None)
    if item is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(item)


@app.route("/api/tasks", methods=["POST"])
def create_task() -> tuple[Response, int]:
    global next_id
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "Request's body should be JSON"}), 400

    error = validate_task_data(data)
    if error:
        return jsonify({"error": error}), 400

    new_task = {
        "id": next_id,
        "title": data["title"],
        "done": data.get("done", False),
        "priority": data.get("priority", "medium"),
        "deadline": data.get("deadline"),
    }
    tasks.append(new_task)
    next_id += 1

    return jsonify(new_task), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id: int) -> tuple[Response, int] | Response:
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request's body should be JSON"}), 400

    error = validate_task_data(data)
    if error:
        return jsonify({"error": error}), 400

    task["title"] = data["title"]
    task["done"] = data.get("done", False)
    task["priority"] = data.get("priority", "medium")
    task["deadline"] = data.get("deadline")

    return jsonify(task)


@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def patch_task(task_id: int) -> tuple[Response, int] | Response:
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request's body should be JSON"}), 400

    error = validate_task_data(data, partial=True)
    if error:
        return jsonify({"error": error}), 400

    # Обновляем только переданные поля
    for field in ("title", "done", "priority", "deadline"):
        if field in data:
            task[field] = data[field]

    return jsonify(task)


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id: int) -> tuple[Response, int] | tuple[str, int]:
    global tasks
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        return jsonify({"error": "Task not found"}), 404

    tasks = [t for t in tasks if t["id"] != task_id]
    return "", 204


@app.route("/api/tasks", methods=["DELETE"])
def delete_all_tasks() -> tuple[Response, int]:
    global tasks
    tasks = []
    return "", 204


@app.route("/api/tasks/bulk", methods=["POST"])
def bulk_create_tasks() -> tuple[Response, int]:
    global next_id
    data = request.get_json(silent=True)

    if not isinstance(data, list):
        return jsonify({"error": "An array of tasks expected"}), 400

    created = []
    for item in data:
        error = validate_task_data(item)
        if error:
            return jsonify({"error": error}), 400

    for item in data:
        new_task = {
            "id": next_id,
            "title": item["title"],
            "done": item.get("done", False),
            "priority": item.get("priority", "medium"),
            "deadline": item.get("deadline"),
        }
        tasks.append(new_task)
        created.append(new_task)
        next_id += 1

    return jsonify({"count": len(created), "created": created}), 201


@app.route("/api/tasks/stats", methods=["GET"])
def get_stats() -> Response:
    done_count = sum(1 for t in tasks if t["done"])
    return jsonify({
        "total": len(tasks),
        "done": done_count,
        "not_done": len(tasks) - done_count,
    })


@app.route("/api/tasks/<int:task_id>/related", methods=["GET"])
def get_related_tasks(task_id: int) -> tuple[Response, int] | Response:
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        return jsonify({"error": "Task not found"}), 404

    related = [t for t in tasks if t["priority"] == task["priority"] and t["id"] != task_id]
    return jsonify({"related": related})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Path not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    app.logger.exception("Unhandled exception")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    print(f"Server running on http://localhost:{port}")
    app.run(port=port, debug=True)
