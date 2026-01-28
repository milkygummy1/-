import sqlite3
import pandas as pd
import os
import random

# Конфигурация БД
DB_NAME = "repair_management.db"

def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # --- 1. Основные таблицы системы заявок ---
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fio TEXT NOT NULL,
        role TEXT DEFAULT 'Сотрудник',
        phone TEXT
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_date TEXT DEFAULT CURRENT_TIMESTAMP,
        address TEXT NOT NULL,
        client_name TEXT NOT NULL,
        client_phone TEXT,
        problem_description TEXT NOT NULL,
        status_id INTEGER,
        employee_id INTEGER,
        FOREIGN KEY (status_id) REFERENCES statuses(id),
        FOREIGN KEY (employee_id) REFERENCES users(id) ON DELETE SET NULL
    );
    ''')

    # --- 2. Таблицы для импорта из Excel ---
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS housing_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT,
        manage_start_date TEXT,
        floors INTEGER,
        apartments_count INTEGER,
        build_year INTEGER,
        area_sqm REAL
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS debts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT,
        flat_number TEXT,
        owner_name TEXT,
        phone TEXT,
        water_debt REAL,
        electricity_debt REAL
    );
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_name TEXT,
        address TEXT,
        flat_number TEXT,
        period TEXT,
        amount_charged REAL,
        amount_paid REAL
    );
    ''')

    # Заполнение статусами
    initial_statuses = [('Открыта заявка',), ('Заявка в работе',), ('Заявка закрыта',)]
    cursor.executemany("INSERT OR IGNORE INTO statuses (name) VALUES (?)", initial_statuses)
    
    conn.commit()
    print("Структура БД создана.")
    return conn

def import_excel_data(conn):
    """Импорт данных с исправлением ошибки Timestamp"""
    
    # --- 1. Жилой фонд (с исправлением ошибки) ---
    if os.path.exists('Список жилого фонда.xlsx'):
        try:
            df = pd.read_excel('Список жилого фонда.xlsx')
            for _, row in df.iterrows():
                # ИСПРАВЛЕНИЕ: Принудительно переводим дату в строку
                raw_date = row.iloc[2]
                date_str = str(raw_date) # Превращает Timestamp('2020-01-01') в строку '2020-01-01 00:00:00'

                conn.execute('''
                    INSERT INTO housing_stock (address, manage_start_date, floors, apartments_count, build_year, area_sqm)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (row.iloc[1], date_str, row.iloc[3], row.iloc[4], row.iloc[5], row.iloc[6]))
            print("Жилой фонд успешно импортирован.")
        except Exception as e:
            print(f"Ошибка импорта жилого фонда: {e}")

    # --- 2. Задолженности ---
    if os.path.exists('Список задолженностей.xlsx'):
        try:
            # header=2, так как обычно в таких отчетах сверху шапка
            df = pd.read_excel('Список задолженностей.xlsx', header=2) 
            for _, row in df.iterrows():
                if pd.notna(row.get('Адрес')): 
                    conn.execute('''
                        INSERT INTO debts (address, flat_number, owner_name, phone, water_debt, electricity_debt)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (row.get('Адрес'), row.get('Квартира'), row.get('Владелец'), row.get('Телефон'), row.get('Вода'), row.get('Электроэнергия')))
            print("Задолженности импортированы.")
        except Exception as e:
            print(f"Ошибка импорта задолженностей: {e}")

    # --- 3. Отчет по оплате ---
    if os.path.exists('Отчет по оплате.xlsx'):
        try:
            df = pd.read_excel('Отчет по оплате.xlsx', header=2)
            for _, row in df.iterrows():
                if pd.notna(row.get('Адрес')):
                    conn.execute('''
                        INSERT INTO payments (owner_name, address, flat_number, period, amount_charged, amount_paid)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (row.get('Собственник'), row.get('Адрес'), row.get('Квартира'), row.get('Период'), row.get('Начислено'), row.get('Оплачено')))
            print("Отчет по оплате импортирован.")
        except Exception as e:
            print(f"Ошибка импорта оплаты: {e}")

    # --- 4. Добавляем сотрудников и ТЕСТОВЫЕ ЗАЯВКИ ---
    cursor = conn.cursor()
    
    # Проверка и добавление сотрудника
    cursor.execute("SELECT count(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (fio, role, phone) VALUES ('Петров Петр Петрович', 'Сантехник', '89005553535')")
        cursor.execute("INSERT INTO users (fio, role, phone) VALUES ('Сидоров Иван Алексеевич', 'Электрик', '89001112233')")
        print("Добавлены тестовые сотрудники.")

    # Генерация тестовых заявок (чтобы главное окно не было пустым)
    cursor.execute("SELECT count(*) FROM requests")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]
        
        test_requests = [
            ("ул. Ленина, д. 10", "Иванов И.И.", "89001234567", "Протекает кран на кухне", 1, user_ids[0] if user_ids else None),
            ("ул. Пушкина, д. 5", "Смирнова А.А.", "89007654321", "Нет света в подъезде", 2, user_ids[1] if len(user_ids) > 1 else None),
            ("ул. Гагарина, д. 12", "Кузнецов В.В.", "89009998877", "Засор в ванной", 3, user_ids[0] if user_ids else None)
        ]
        
        cursor.executemany('''
            INSERT INTO requests (address, client_name, client_phone, problem_description, status_id, employee_id) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', test_requests)
        print("Созданы 3 тестовые заявки для демонстрации.")

    conn.commit()

if __name__ == "__main__":
    try:
        connection = create_database()
        import_excel_data(connection)
        connection.close()
        print("\n--- ВСЕ ГОТОВО ---")
        print("Теперь запустите main.py. В таблице должны появиться заявки.")
    except Exception as e:
        print(f"Критическая ошибка: {e}")