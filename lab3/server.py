from datetime import datetime
from math import isfinite

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import BadRequest, HTTPException, NotFound

app = Flask(__name__)
app.json.ensure_ascii = False
port = 8080

# Идентификатор обозначает запись, поиск не зависит от позиции в списке.
brands = [
    {"id": 1, "name": "PetCare"},
    {"id": 2, "name": "HappyPet"},
]
categories = ["food", "toys"]
products = [
    {
        "id": 1,
        "name": "Корм для кошек",
        "price": 400,
        "stock": 12,
        "category": "food",
        "brand_id": 1,
    },
    {
        "id": 2,
        "name": "Корм для собак",
        "price": 1200,
        "stock": 8,
        "category": "food",
        "brand_id": 2,
    },
    {
        "id": 3,
        "name": "Мяч для кошки",
        "price": 300,
        "stock": 0,
        "category": "toys",
        "brand_id": 1,
    },
    {
        "id": 4,
        "name": "Игрушка для собаки",
        "price": 600,
        "stock": 5,
        "category": "toys",
        "brand_id": 2,
    },
]
reviews = [
    {"id": 1, "product_id": 1, "author": "Анна", "text": "Кошке понравился корм"},
    {"id": 2, "product_id": 1, "author": "Иван", "text": "Удобная упаковка"},
    {"id": 3, "product_id": 2, "author": "Ольга", "text": "Хороший состав"},
]


def positive_integer(value: str, name: str) -> int:
    """Преобразует строку в положительное целое или вызывает ошибку 400."""
    # Сначала проверяем формат и длину, затем значение полученного числа.
    if not value.isascii() or not value.isdecimal() or len(value) > 10:
        raise BadRequest(f"{name} must be a positive integer")
    number = int(value)
    if number < 1:
        raise BadRequest(f"{name} must be a positive integer")
    return number


def find_record(records: list[dict], value: str, name: str) -> dict:
    """Находит запись по ID или вызывает ошибку 400 либо 404."""
    # После проверки формата ищем совпадение по полю id, независимо от индекса.
    record_id = positive_integer(value, f"{name}_id")
    record = next((item for item in records if item["id"] == record_id), None)
    if record is None:
        raise NotFound(f"{name.capitalize()} not found")
    return record


def category_products(category: str) -> list[dict]:
    """Возвращает товары категории или вызывает ошибку 404."""
    # Отсутствующая категория отличается от существующей без товаров.
    if category not in categories:
        raise NotFound("Category not found")
    return [product for product in products if product["category"] == category]


def collection_response(source: list[dict]) -> Response:
    """Возвращает страницу товаров после проверки query-параметров."""
    # Сначала отклоняем неизвестные имена и недопустимые повторения параметров.
    allowed = {"search", "sort", "order", "page", "limit", "filter"}
    for name in request.args:
        if name not in allowed:
            raise BadRequest(f"Unknown query parameter: {name}")
        if name != "filter" and len(request.args.getlist(name)) != 1:
            raise BadRequest(f"Query parameter must occur once: {name}")

    # casefold позволяет сравнивать названия без учёта регистра.
    search = request.args.get("search", "")
    if len(search) > 100:
        raise BadRequest("search must contain at most 100 characters")
    result = [item for item in source if search.casefold() in item["name"].casefold()]

    # Повторение filter задаёт несколько условий, объединённых логическим И.
    for expression in request.args.getlist("filter"):
        field, separator, value = expression.partition(":")
        if not separator or not value or field not in ("category", "price"):
            raise BadRequest("filter must be category:value or price:value")
        if field == "price":
            try:
                price = float(value)
            except (ValueError, OverflowError) as error:
                raise BadRequest(
                    "Filter price must be a finite non-negative number"
                ) from error
            # float распознаёт NaN и бесконечность, поэтому проверяем конечность.
            if not isfinite(price) or price < 0:
                raise BadRequest("Filter price must be a finite non-negative number")
            result = [item for item in result if item["price"] == price]
        else:
            result = [item for item in result if item["category"] == value]

    # Белый список полей защищает обращение к ключам словарей при сортировке.
    sort = request.args.get("sort", "id")
    order = request.args.get("order", "asc")
    if sort not in ("id", "name", "price", "stock"):
        raise BadRequest("sort must be id, name, price or stock")
    if order not in ("asc", "desc"):
        raise BadRequest("order must be asc or desc")
    result = sorted(result, key=lambda item: item[sort], reverse=order == "desc")

    # Отсутствующие параметры страницы получают значения по умолчанию.
    page = positive_integer(request.args.get("page", "1"), "page")
    limit = positive_integer(request.args.get("limit", "10"), "limit")
    if limit > 100:
        raise BadRequest("limit must be between 1 and 100")
    # count относится ко всей выборке, items - только к текущей странице.
    count = len(result)
    # Нумерация страниц начинается от 1, индексы среза начинаются от 0.
    start = (page - 1) * limit
    return jsonify(
        {
            "count": count,
            "page": page,
            "limit": limit,
            "totalPages": (count + limit - 1) // limit,
            "items": result[start : start + limit],
        }
    )


@app.before_request
def log_request() -> None:
    """Выводит время, метод, URL и IP клиента перед обработкой каждого запроса."""
    # Удаляем завершающий вопросительный знак для адреса без query-параметров.
    print(
        f"{datetime.now().isoformat()} {request.method} "
        f"{request.full_path.rstrip('?')} IP={request.remote_addr}",
        flush=True,
    )


@app.get("/products")
def get_products() -> Response:
    """Возвращает страницу общей коллекции товаров."""
    # Передаём весь список общему обработчику поиска, фильтров и пагинации.
    return collection_response(products)


@app.get("/products/stats")
def get_stats() -> Response:
    """Возвращает количество товаров и показатели цены всей коллекции."""
    # Для пустого списка значения цен будут null, деление на ноль исключено.
    prices = [product["price"] for product in products]
    return jsonify(
        {
            "count": len(prices),
            "average_price": sum(prices) / len(prices) if prices else None,
            "min_price": min(prices, default=None),
            "max_price": max(prices, default=None),
        }
    )


@app.get("/products/<product_id>")
def get_product(product_id: str) -> Response:
    """Возвращает товар по переданному идентификатору."""
    # Общий поиск проверяет ID и прерывает запрос при отсутствии товара.
    return jsonify({"product": find_record(products, product_id, "product")})


@app.get("/products/<product_id>/reviews")
def get_reviews(product_id: str) -> Response:
    """Возвращает все отзывы существующего товара и их количество."""
    # Сначала проверяем товар, затем отбираем отзывы по внешнему ключу product_id.
    product = find_record(products, product_id, "product")
    result = [review for review in reviews if review["product_id"] == product["id"]]
    return jsonify({"count": len(result), "reviews": result})


@app.get("/products/<product_id>/related")
def get_related(product_id: str) -> Response:
    """Возвращает другие товары той же категории."""
    # Исключаем исходный товар по ID, несмотря на совпадающую категорию.
    product = find_record(products, product_id, "product")
    result = [
        item
        for item in products
        if item["category"] == product["category"] and item["id"] != product["id"]
    ]
    return jsonify({"count": len(result), "items": result})


@app.get("/categories/<category>/products")
def get_category_products(category: str) -> Response:
    """Возвращает страницу товаров выбранной категории."""
    # Сначала ограничиваем коллекцию категорией, затем применяем query-параметры.
    return collection_response(category_products(category))


@app.get("/categories/<category>/products/<product_id>")
def get_category_product(category: str, product_id: str) -> Response:
    """Возвращает товар, принадлежащий указанной категории."""
    # Ищем внутри категории, чтобы ID товара другой категории давал 404.
    source = category_products(category)
    product = find_record(source, product_id, "product")
    return jsonify({"category": category, "product": product})


@app.get("/brands")
def get_brands() -> Response:
    """Возвращает список всех брендов и количество записей."""
    # Бренды передаются целиком, параметры выборки предусмотрены для товаров.
    return jsonify({"count": len(brands), "brands": brands})


@app.get("/brands/<brand_id>/products")
def get_brand_products(brand_id: str) -> Response:
    """Возвращает страницу товаров существующего бренда."""
    # Проверяем бренд до выборки, чтобы неизвестный ID возвращал 404.
    brand = find_record(brands, brand_id, "brand")
    return collection_response(
        [product for product in products if product["brand_id"] == brand["id"]]
    )


def brand_product(brand_id: str, product_id: str) -> tuple[dict, dict]:
    """Возвращает бренд и товар после проверки их существования и связи."""
    # Наличия двух записей недостаточно, товар должен относиться к этому бренду.
    brand = find_record(brands, brand_id, "brand")
    product = find_record(products, product_id, "product")
    if product["brand_id"] != brand["id"]:
        raise NotFound("Product not found in this brand")
    return brand, product


@app.get("/brands/<brand_id>/products/<product_id>")
def get_brand_product(brand_id: str, product_id: str) -> Response:
    """Возвращает бренд и принадлежащий ему товар."""
    # Используем общую проверку связи для обоих маршрутов товара бренда.
    brand, product = brand_product(brand_id, product_id)
    return jsonify({"brand": brand, "product": product})


@app.get("/brands/<brand_id>/products/<product_id>/reviews/<review_id>")
def get_brand_product_review(
    brand_id: str, product_id: str, review_id: str
) -> Response:
    """Возвращает отзыв после проверки цепочки бренд, товар и отзыв."""
    # Проверяем принадлежность товара бренду и принадлежность отзыва товару.
    brand, product = brand_product(brand_id, product_id)
    review = find_record(reviews, review_id, "review")
    if review["product_id"] != product["id"]:
        raise NotFound("Review not found for this product")
    return jsonify({"brand": brand, "product": product, "review": review})


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException) -> Response:
    """Преобразует HTTP-ошибку в JSON, сохраняя её статус и заголовки."""
    # Готовый ответ сохраняет служебные заголовки, например Allow для 405.
    response = error.get_response()
    response.data = app.json.dumps({"error": error.description})
    response.content_type = "application/json"
    return response


@app.errorhandler(404)
def handle_not_found(error: NotFound) -> tuple[Response, int]:
    """Возвращает JSON для отсутствующего маршрута, записи или связи."""
    # Flask вызывает обработчик и при отсутствии маршрута, и при raise NotFound.
    message = error.description
    if message == NotFound.description:
        message = "Route not found"
    return jsonify({"error": message}), 404


@app.errorhandler(Exception)
def handle_unexpected_error(error: Exception) -> tuple[Response, int]:
    """Записывает непредвиденное исключение и возвращает ошибку 500."""
    # Подробности сохраняются в журнале, клиенту передаётся общее сообщение.
    app.logger.exception("Unhandled exception")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(port=port, debug=True)
