-- Внешние ключи включаются отдельно для каждого соединения в Python.
-- Начальная схема и данные создаются одной транзакцией.
BEGIN IMMEDIATE;

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0)
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    price REAL NOT NULL CHECK (typeof(price) IN ('real', 'integer') AND price >= 0),
    stock INTEGER NOT NULL CHECK (typeof(stock) = 'integer' AND stock >= 0),
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT
);

-- Один индекс помогает отбору товаров категории и сортировке по цене внутри неё.
CREATE INDEX idx_products_category_price ON products(category_id, price);

INSERT INTO categories (name) VALUES
    ('Корм'), ('Игрушки'), ('Аксессуары'), ('Уход');

INSERT INTO products (name, price, stock, category_id) VALUES
    ('Корм для кошек', 400, 12, 1),
    ('Корм для собак', 1200, 8, 1),
    ('Мяч для кошки', 300, 0, 2),
    ('Игрушка для собаки', 600, 5, 2),
    ('Миска', 250, 10, 3),
    ('Поводок', 900, 4, 3);

PRAGMA user_version = 1;
COMMIT;
