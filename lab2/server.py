import logging
from datetime import date, datetime
from pathlib import Path

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
port = 3001

# Журнал находится в каталоге сервера независимо от рабочего каталога.
access_logger = logging.getLogger(__name__ + ".access")
access_logger.setLevel(logging.INFO)
access_logger.propagate = False
if not access_logger.handlers:
    file_handler = logging.FileHandler(
        Path(__file__).with_name("access.log"), encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    access_logger.addHandler(file_handler)

TASK_FIELDS = ("title", "done", "priority", "deadline")


# Список живёт в памяти процесса. При перезапуске загружаются эти исходные задачи.
tasks = [
    {
        "id": 0,
        "title": "Первая задача",
        "done": False,
        "priority": "high",
        "deadline": "2026-09-16",
    },
    {
        "id": 1,
        "title": "Вторая задача",
        "done": True,
        "priority": "low",
        "deadline": "2026-12-25",
    },
    {
        "id": 2,
        "title": "Третья задача",
        "done": False,
        "priority": "medium",
        "deadline": "2026-09-20",
    },
]

# Стартовые ID идут от нуля без пропусков. После удаления счётчик не уменьшается,
# поэтому новая задача получает новый ID независимо от текущей длины списка.
next_id = max((task["id"] for task in tasks), default=-1) + 1


def validate_task_data(data: object, partial: bool = False) -> str | None:
    """Возвращает текст ошибки или None, если всё ок."""
    if not isinstance(data, dict):
        return "A JSON object is required"

    # POST и PUT требуют title. Для PATCH проверяем только переданные поля.
    if not partial and "title" not in data:
        return "Title is required"

    if "title" in data and not isinstance(data["title"], str):
        return "Title must be a string"

    if "title" in data and not data["title"].strip():
        return "Title must not be empty"

    deadline = data.get("deadline")
    if deadline is not None:
        if not isinstance(deadline, str):
            return "Deadline must be a date in YYYY-MM-DD format or null"
        try:
            parsed_date = date.fromisoformat(deadline)
        except ValueError:
            return "Deadline must be a valid date in YYYY-MM-DD format"
        if parsed_date.isoformat() != deadline:
            return "Deadline must use YYYY-MM-DD format"

    if "done" in data and not isinstance(data["done"], bool):
        return "Done must be a boolean"

    if "priority" in data and data["priority"] not in ("low", "medium", "high"):
        return "Priority must be one of [low, medium, high]"

    return None


def find_task(task_id: int) -> dict | None:
    """Один способ поиска задачи для всех маршрутов."""
    return next((task for task in tasks if task["id"] == task_id), None)


def task_fields(data: dict) -> dict:
    """Общие значения полей по умолчанию для POST и PUT."""
    return {
        "title": data["title"],
        "done": data.get("done", False),
        "priority": data.get("priority", "medium"),
        "deadline": data.get("deadline"),
    }


@app.before_request
def log_request() -> None:
    # Flask вызывает эту функцию перед обработкой запроса, даже для неизвестного пути.
    timestamp = datetime.now().isoformat()
    log_line = f"{timestamp} {request.method} {request.full_path.rstrip('?')}"
    print(log_line)
    access_logger.info(log_line)


@app.route("/", methods=["GET"])
def index() -> Response:
    return jsonify({"message": "Welcome, that's my server!"})


@app.route("/api/tasks", methods=["GET"])
def get_tasks() -> tuple[Response, int] | Response:
    # Копируем список для обработки выборки. Словари внутри только читаются.
    result = tasks.copy()

    # Сначала ищем подстроку в названии без учёта регистра.
    search = request.args.get("search")
    if search:
        result = [t for t in result if search.lower() in t["title"].lower()]

    # Разрешаем сортировку по известным полям до разбиения результата на страницы.
    sort_field = request.args.get("sort")
    order = request.args.get("order", "asc")
    if order not in ("asc", "desc"):
        return jsonify({"error": "order must be asc or desc"}), 400
    if sort_field:
        if sort_field not in ("id", "title", "priority", "deadline", "done"):
            return jsonify({"error": f"Can't sort by {sort_field}"}), 400
        reverse = order == "desc"
        # Отсутствующие сроки всегда идут в конце при любом направлении.
        present = [task for task in result if task[sort_field] is not None]
        missing = [task for task in result if task[sort_field] is None]
        result = (
            sorted(present, key=lambda task: task[sort_field], reverse=reverse)
            + missing
        )

    # Первая страница имеет номер 1. Первый индекс списка в Python равен 0.
    if "page" in request.args or "limit" in request.args:
        page = request.args.get("page", type=int)
        limit = request.args.get("limit", type=int)
        if page is None or limit is None or page < 1 or limit < 1:
            return jsonify(
                {"error": "page and limit must both be positive integers"}
            ), 400
        start = (page - 1) * limit
        end = start + limit
        result = result[start:end]

    # count показывает размер выдачи после поиска и пагинации.
    return jsonify({"count": len(result), "tasks": result})


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id: int) -> tuple[Response, int] | Response:
    # Конвертер <int:task_id> передаёт число. next берёт первое совпадение
    # или возвращает None, если нужный ID отсутствует.
    item = find_task(task_id)
    if item is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(item)


@app.route("/api/tasks", methods=["POST"])
def create_task() -> tuple[Response, int]:
    global next_id
    # silent=True даёт None при ошибке разбора, чтобы вернуть свою JSON-ошибку.
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "Request's body should be JSON"}), 400

    error = validate_task_data(data)
    if error:
        return jsonify({"error": error}), 400

    # ID назначает сервер. Необязательные поля получают значения по умолчанию.
    new_task = {"id": next_id, **task_fields(data)}
    tasks.append(new_task)
    next_id += 1

    return jsonify(new_task), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id: int) -> tuple[Response, int] | Response:
    task = find_task(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request's body should be JSON"}), 400

    error = validate_task_data(data)
    if error:
        return jsonify({"error": error}), 400

    # PUT заменяет поля задачи, пропущенные необязательные поля получают
    # значения по умолчанию. ID остаётся прежним.
    task.update(task_fields(data))

    return jsonify(task)


@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def patch_task(task_id: int) -> tuple[Response, int] | Response:
    task = find_task(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request's body should be JSON"}), 400

    error = validate_task_data(data, partial=True)
    if error:
        return jsonify({"error": error}), 400

    # PATCH меняет только переданные поля из списка. ID клиент поменять не может.
    for field in TASK_FIELDS:
        if field in data:
            task[field] = data[field]

    return jsonify(task)


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id: int) -> tuple[Response, int] | tuple[str, int]:
    global tasks
    task = find_task(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404

    # Собираем список без удалённой задачи. Для ответа 204 тело должно быть пустым.
    tasks = [t for t in tasks if t["id"] != task_id]
    return "", 204


@app.route("/api/tasks", methods=["DELETE"])
def delete_all_tasks() -> tuple[str, int]:
    global tasks
    # Список очищается до формирования ответа. Счётчик ID сохраняется.
    tasks = []
    return "", 204


@app.route("/api/tasks/bulk", methods=["POST"])
def bulk_create_tasks() -> tuple[Response, int]:
    global next_id
    data = request.get_json(silent=True)

    if not isinstance(data, list):
        return jsonify({"error": "An array of tasks expected"}), 400

    created = []
    # Сначала проверяем весь пакет. Ошибка в одной записи прерывает запрос
    # до добавления задач и изменения счётчика.
    for item in data:
        error = validate_task_data(item)
        if error:
            return jsonify({"error": error}), 400

    for item in data:
        new_task = {"id": next_id, **task_fields(item)}
        tasks.append(new_task)
        created.append(new_task)
        next_id += 1

    return jsonify({"count": len(created), "created": created}), 201


@app.route("/api/tasks/stats", methods=["GET"])
def get_stats() -> Response:
    # Считаем выполненные задачи по текущему списку после всех изменений.
    done_count = sum(1 for t in tasks if t["done"])
    return jsonify(
        {
            "total": len(tasks),
            "done": done_count,
            "not_done": len(tasks) - done_count,
        }
    )


@app.route("/api/tasks/<int:task_id>/related", methods=["GET"])
def get_related_tasks(task_id: int) -> tuple[Response, int] | Response:
    task = find_task(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404

    # Связь здесь определяется общим приоритетом. Исходную задачу исключаем.
    related = [
        t for t in tasks if t["priority"] == task["priority"] and t["id"] != task_id
    ]
    return jsonify({"related": related})


@app.errorhandler(404)
def not_found(e):
    # Здесь обрабатывается неизвестный маршрут. Отсутствующую задачу находят
    # в самих обработчиках, которые возвращают 404 и сообщение Task not found.
    return jsonify({"error": "Path not found"}), 404


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException) -> Response:
    # Сохраняем статус и заголовки Flask, включая Allow для ошибки 405.
    response = error.get_response()
    response.data = app.json.dumps({"error": error.description})
    response.content_type = "application/json"
    return response


@app.errorhandler(Exception)
def handle_unexpected_error(error: Exception) -> tuple[Response, int]:
    app.logger.exception("Unhandled exception")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # Прямой запуск поднимает сервер, импорт позволяет проверить app отдельно.
    print(f"Server running on http://localhost:{port}")
    app.run(port=port, debug=True)
