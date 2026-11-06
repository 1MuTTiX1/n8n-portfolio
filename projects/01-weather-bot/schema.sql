-- Schema for Weather Bot (n8n project)
-- Database: PostgreSQL
-- Author: 1MuTTiX1

-- Таблица пользователей бота
CREATE TABLE public.bot_users (
    telegram_id int8 NOT NULL,
    notify_time time NULL,
    timezone text NULL,
    notify_on bool NULL,
    created_at timestamptz NULL,
    CONSTRAINT bot_users_pkey PRIMARY KEY (telegram_id)
);

-- Основной справочник локаций (ГАР)
CREATE TABLE public.ru_locations (
    id uuid NOT NULL,
    gar_object_id int8 NULL,
    parent_id uuid NULL,
    region_id uuid NULL,
    region_code int2 NULL,
    name text NULL,
    type_name text NULL,
    gar_level int2 NULL,
    kind text NULL,
    lat float8 NULL,
    lon float8 NULL,
    coord_source text NULL,
    is_popular bool NULL,
    sort_order int2 NULL,
    updated_at timestamptz NULL,
    name_prep text NULL,
    CONSTRAINT ru_locations_pkey PRIMARY KEY (id)
);

-- Связь пользователей и выбранных ими локаций
CREATE TABLE public.user_locations (
    telegram_id int8 NOT NULL,
    location_id uuid NOT NULL,
    is_primary bool NULL,
    created_at timestamptz NULL,
    CONSTRAINT user_locations_pkey PRIMARY KEY (telegram_id, location_id),
    CONSTRAINT user_locations_telegram_id_fkey FOREIGN KEY (telegram_id) REFERENCES public.bot_users(telegram_id),
    CONSTRAINT user_locations_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.ru_locations(id)
);

-- (Опционально) Промежуточная таблица для импорта, которую ты использовал
CREATE TABLE public.ru_locations_stage (
    id text NULL,
    gar_object_id text NULL,
    parent_id text NULL,
    region_id text NULL,
    region_code text NULL,
    name text NULL,
    type_name text NULL,
    gar_level text NULL,
    kind text NULL
);