import argparse
import json
import sqlite3
from pathlib import Path

DEFAULT_DATABASE = Path(__file__).with_name("lab4.db")


def connect_database(path: Path) -> sqlite3.Connection:
    """Открывает базу, включает внешние ключи и применяет начальную миграцию."""
    # Явные BEGIN и COMMIT управляют транзакциями без неявного открытия.
    connection = sqlite3.connect(path, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            # Чужую схему без номера версии нельзя считать пустой учебной базой.
            existing = connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if existing:
                raise ValueError("База содержит таблицы без версии миграции")
            migration = Path(__file__).with_name("init_db.sql").read_text()
            connection.executescript(migration)
            print("\n=== Создание схемы и начальных данных ===")
            print(migration)
            print("Созданы 4 категории, 6 товаров и индекс. Версия базы 1.")
        elif version != 1:
            raise ValueError(f"Неподдерживаемая версия базы: {version}")
    except Exception:
        # При ошибке миграции откатываем незавершённую транзакцию и закрываем файл.
        if connection.in_transaction:
            connection.rollback()
        connection.close()
        raise
    return connection


def show_query(
    connection: sqlite3.Connection,
    title: str,
    sql: str,
    parameters: tuple = (),
) -> None:
    """Выполняет SELECT и выводит SQL, параметры и строки результата."""
    # Row преобразуется в словарь, чтобы в выводе сохранить названия столбцов.
    rows = connection.execute(sql, parameters).fetchall()
    print(f"\n=== {title} ===")
    print(sql.strip())
    if parameters:
        print("Параметры " + json.dumps(parameters, ensure_ascii=False))
    print(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2))


def demonstrate_changes(connection: sqlite3.Connection) -> None:
    """Показывает обновление и удаление записи внутри подтверждаемой транзакции."""
    # Изменяем файл базы, любая ошибка приводит к отмене двух операций.
    print("\n=== UPDATE и DELETE ===")
    print("BEGIN")
    connection.execute("BEGIN")
    try:
        connection.execute("UPDATE products SET price = ? WHERE id = ?", (450, 1))
        print("UPDATE products SET price = ? WHERE id = ?")
        print("Параметры [450, 1]")
        cursor = connection.execute("DELETE FROM products WHERE id = ?", (6,))
        print("DELETE FROM products WHERE id = ?")
        print("Параметры [6]")
        print(f"Удалено записей {cursor.rowcount}")
        connection.commit()
        print("COMMIT")
    except Exception:
        connection.rollback()
        raise
    show_query(
        connection,
        "Состояние после COMMIT",
        "SELECT id, name, price, stock, category_id FROM products ORDER BY id",
    )


def demonstrate_rollback(connection: sqlite3.Connection) -> None:
    """Показывает отмену всех изменений при нарушении ограничения остатка."""
    # Первая операция допустима, вторая нарушает CHECK, поэтому отменяем изменения.
    print("\n=== Транзакция, завершённая ROLLBACK ===")
    print("BEGIN")
    connection.execute("BEGIN")
    try:
        print("UPDATE products SET stock = stock + 1 WHERE id = 1")
        connection.execute("UPDATE products SET stock = stock + 1 WHERE id = 1")
        print("UPDATE products SET stock = -1 WHERE id = 2")
        connection.execute("UPDATE products SET stock = -1 WHERE id = 2")
        connection.commit()
    except sqlite3.IntegrityError as error:
        connection.rollback()
        print(f"Нарушено ограничение: {error}")
        print("ROLLBACK")
    except Exception:
        connection.rollback()
        raise
    show_query(
        connection,
        "Остатки после ROLLBACK",
        "SELECT id, stock FROM products WHERE id IN (?, ?) ORDER BY id",
        (1, 2),
    )


def run_demo(connection: sqlite3.Connection) -> None:
    """Выполняет запросы всех уровней варианта 3 в заданном порядке."""
    # Сначала исследуем исходные данные, затем демонстрируем изменение состояния.
    show_query(
        connection,
        "Схема таблиц и индекс",
        "SELECT type, name, sql FROM sqlite_schema "
        "WHERE name IN ('categories', 'products', 'idx_products_category_price') "
        "ORDER BY type, name",
    )
    show_query(connection, "Список категорий", "SELECT * FROM categories ORDER BY id")
    show_query(connection, "Список товаров", "SELECT * FROM products ORDER BY id")
    show_query(
        connection,
        "WHERE: товары в наличии",
        "SELECT id, name, stock FROM products WHERE stock > ? ORDER BY id",
        (0,),
    )
    show_query(
        connection,
        "ORDER BY: название по возрастанию",
        "SELECT id, name FROM products ORDER BY name ASC, id ASC",
    )
    show_query(
        connection,
        "ORDER BY: цена по убыванию",
        "SELECT id, name, price FROM products ORDER BY price DESC, id ASC",
    )
    # Уникальный дополнительный ключ сортировки делает страницы устойчивыми.
    for page in (1, 2):
        show_query(
            connection,
            f"LIMIT и OFFSET: страница {page}",
            "SELECT id, name, price FROM products ORDER BY id LIMIT ? OFFSET ?",
            (3, (page - 1) * 3),
        )
    show_query(
        connection,
        "LIKE: поиск по подстроке",
        "SELECT id, name FROM products WHERE name LIKE ? ORDER BY id",
        ("%Корм%",),
    )
    show_query(
        connection,
        "BETWEEN: диапазон цен",
        "SELECT id, name, price FROM products WHERE price BETWEEN ? AND ? ORDER BY id",
        (300, 600),
    )
    show_query(
        connection,
        "IN: товары выбранных категорий",
        "SELECT id, name, category_id FROM products "
        "WHERE category_id IN (?, ?) ORDER BY id",
        (1, 3),
    )
    show_query(
        connection,
        "Агрегатные функции",
        "SELECT COUNT(*) AS count, SUM(price) AS total_price, "
        "AVG(price) AS average_price, MIN(price) AS min_price, "
        "MAX(price) AS max_price FROM products",
    )
    show_query(
        connection,
        "GROUP BY: товары по категориям",
        "SELECT category_id, COUNT(*) AS count, AVG(price) AS average_price "
        "FROM products GROUP BY category_id ORDER BY category_id",
    )
    show_query(
        connection,
        "INNER JOIN: товары и категории",
        "SELECT p.id, p.name, p.price, c.name AS category FROM products AS p "
        "INNER JOIN categories AS c ON c.id = p.category_id ORDER BY p.id",
    )
    show_query(
        connection,
        "LEFT JOIN: все категории",
        "SELECT c.name AS category, COUNT(p.id) AS product_count "
        "FROM categories AS c LEFT JOIN products AS p ON p.category_id = c.id "
        "GROUP BY c.id, c.name ORDER BY c.id",
    )
    show_query(
        connection,
        "GROUP BY и HAVING",
        "SELECT c.name AS category, COUNT(p.id) AS product_count, "
        "AVG(p.price) AS average_price FROM categories AS c "
        "INNER JOIN products AS p ON p.category_id = c.id "
        "GROUP BY c.id, c.name HAVING AVG(p.price) > ? ORDER BY c.id",
        (500,),
    )
    show_query(
        connection,
        "Подзапрос: цена выше средней",
        "SELECT id, name, price FROM products "
        "WHERE price > (SELECT AVG(price) FROM products) ORDER BY id",
    )
    show_query(
        connection,
        "План индексного поиска",
        "EXPLAIN QUERY PLAN SELECT id, name, price FROM products "
        "WHERE category_id = ? ORDER BY price",
        (1,),
    )
    demonstrate_changes(connection)
    demonstrate_rollback(connection)


def main() -> None:
    """Получает путь базы, запускает демонстрацию и освобождает соединение."""
    # Пользователь может выбрать другой файл, исходная база удалению не подвергается.
    parser = argparse.ArgumentParser(description="Лабораторная 4: SQL и SQLite")
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DATABASE, help="Путь файла SQLite"
    )
    arguments = parser.parse_args()
    connection = connect_database(arguments.db)
    try:
        run_demo(connection)
    finally:
        # Закрываем соединение явно, независимо от результата демонстрации.
        connection.close()


if __name__ == "__main__":
    main()
