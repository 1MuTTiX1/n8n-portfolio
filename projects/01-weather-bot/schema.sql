-- Схема базы данных для проекта Weather Bot (V2)

-- 1. Таблица пользователей (подписчиков)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Таблица локаций (с поддержкой иерархии: город -> район)
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) DEFAULT 'city', -- 'city' для города, 'district' для района
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    parent_id INTEGER REFERENCES locations(id) ON DELETE CASCADE, -- Ссылка на город, если это район
    osm_id BIGINT, -- ID локации в OpenStreetMap
    UNIQUE(name, parent_id) -- Защита от дублей в рамках одного родителя
);

-- 3. Таблица подписок (связь пользователей и локаций)
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, location_id) -- Один пользователь = одна подписка на конкретный район
);

-- 4. Таблица истории погоды (привязана к локации)
CREATE TABLE IF NOT EXISTS weather_history (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE,
    temperature NUMERIC(5, 2),
    windspeed NUMERIC(5, 2),
    condition VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);