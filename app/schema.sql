CREATE TABLE IF NOT EXISTS lecturers (
    uuid TEXT,
    title_before TEXT,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    last_name TEXT NOT NULL,
    title_after TEXT,
    picture_url TEXT,
    location TEXT,
    claim TEXT,
    bio TEXT,
    tags TEXT,
    price_per_hour INTEGER,
    contact TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    uuid TEXT NOT NULL,
    name TEXT NOT NULL
);