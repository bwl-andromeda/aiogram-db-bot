# Функция для инициализации базы данных
async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            -- Создание таблицы пользователей
            CREATE TABLE IF NOT EXISTS users (                
                user_id BIGINT UNIQUE PRIMARY KEY,            -- Уникальный Telegram ID пользователя
                full_name TEXT,                               -- Полное имя пользователя
                balance NUMERIC DEFAULT 0                     -- Текущий баланс пользователя (изменяется с учетом трат и пополнений)
            );

            -- Создание таблицы категорий расходов
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,                        -- Уникальный идентификатор категории
                name TEXT,                                    -- Название категории (например, "Еда", "Транспорт")
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE  -- Привязка к пользователю, удаляется при удалении пользователя
            );

            -- Создание таблицы транзакций
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,                        -- Уникальный идентификатор транзакции
                amount NUMERIC,                               -- Сумма транзакции (положительная для пополнения, отрицательная для траты)
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,  -- Категория, к которой относится транзакция, может быть NULL при удалении категории
                description TEXT,                             -- Описание транзакции
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE, -- Привязка транзакции к пользователю, удаляется при удалении пользователя
                is_income BOOLEAN,                            -- Флаг, указывающий, является ли транзакция доходом (True) или расходом (False)
                created_at TIMESTAMP DEFAULT NOW()            -- Время создания транзакции
            );
        """
        )
        print("Database tables created (if not exist).")
