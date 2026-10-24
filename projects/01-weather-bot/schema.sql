-- Схема базы данных для проекта Weather Bot
CREATE TABLE IF NOT EXISTS weather_history (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    temperature NUMERIC(5, 2),
    windspeed NUMERIC(5, 2),
    condition VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Индекс для быстрого поиска по городу и дате
CREATE INDEX IF NOT EXISTS idx_weather_city_created ON weather_history(city, created_at DESC);