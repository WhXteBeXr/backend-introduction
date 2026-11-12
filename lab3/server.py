from flask import Flask, Response, jsonify

app = Flask(__name__)
port = 8080

products = [
    {"id": 0, "name": "cat food", "price": 400, "category": "cats",
     "reviews": ["That's a good cat food review"]},
    {"id": 1, "name": "dog food", "price": 1200, "category": "dogs",
     "reviews": ["That's a good dog food review"]},
    {"id": 2, "name": "cat toy", "price": 289, "category": "cats",
     "reviews": ["Ordinary cat toy review"]},
    {"id": 3, "name": "another cat toy", "price": 589, "category": "cats",
     "reviews": ["Brilliant cat toy review"]},
]

categories = ["cats", "dogs"]


def is_product_id_valid(product_id: int) -> bool:
    if not isinstance(product_id, int) or product_id >= len(products):
        return False
    return True


@app.route("/api/products", methods=["GET"])
def get_products() -> Response:
    return jsonify({"products": products})


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id) -> tuple[Response, int]:
    if not is_product_id_valid(product_id):
        return jsonify({"error": "invalid task id"}), 400

    # Проверить надобность этой проверки
    product = products[product_id]
    if product not in products:
        return jsonify({"error": "Product not found"}), 404

    return jsonify({"product": products[product_id]}), 200


@app.route("/api/products/<int:product_id>/reviews", methods=["PUT"])
def get_related_product(product_id) -> tuple[Response, int]:
    if not is_product_id_valid(product_id):
        return jsonify({"error": "invalid task id"}), 400

    product_reviews = products[product_id]["reviews"]
    return jsonify({"product": products[product_id], "reviews": product_reviews}), 200


@app.route("/api/products/<string:category>/items", methods=["GET"])
def get_products_by_category(category) -> tuple[Response, int]:
    if not isinstance(category, str):
        return jsonify({"error": "invalid category"}), 400

    if category not in categories:
        return jsonify({"error": "category didn't exist"}), 404

    filtered_products = [p for p in products if p["category"] == category]
    return jsonify({"products": filtered_products}), 200


@app.errorhandler(404)
def not_found(error) -> tuple[Response, int]:
    return jsonify({"error": "page not found"}), 404


@app.errorhandler(500)
def server_error(error) -> tuple[Response, int]:
    return jsonify({"error": "internal server error"}), 500


if __name__ == '__main__':
    app.run(port=port, debug=True)
