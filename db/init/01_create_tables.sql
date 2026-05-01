-- =============================================================================
-- TMDB Movie Recommender – PostgreSQL Schema
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Core entity: MOVIE
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS movie (
    movie_id          BIGINT          PRIMARY KEY,
    title             VARCHAR(255)    NOT NULL,
    original_title    VARCHAR(255),
    overview          TEXT,
    release_date      DATE,
    runtime           INT,
    original_language VARCHAR(10),
    status            VARCHAR(50),
    imdb_id           VARCHAR(20)     UNIQUE,       -- globally unique IMDB identifier
    popularity        DECIMAL(12, 4),
    vote_average      DECIMAL(5, 3),                -- TMDB returns values like 8.203
    vote_count        INT,
    adult_flag        BOOLEAN,
    video_flag        BOOLEAN,
    poster_path       VARCHAR(255),
    backdrop_path     VARCHAR(255),
    homepage          TEXT,
    tagline           TEXT,
    budget            BIGINT,
    revenue           BIGINT,
    collection_id     BIGINT,
    collection_name   VARCHAR(255)
);

-- ---------------------------------------------------------------------------
-- GENRE  +  MOVIE_GENRE  (M:N)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS genre (
    genre_id    INT             PRIMARY KEY,
    genre_name  VARCHAR(100)    NOT NULL UNIQUE     -- genre names are globally unique
);

CREATE TABLE IF NOT EXISTS movie_genre (
    movie_id    BIGINT  NOT NULL,
    genre_id    INT     NOT NULL,
    PRIMARY KEY (movie_id, genre_id),
    FOREIGN KEY (movie_id)  REFERENCES movie(movie_id)  ON DELETE CASCADE,
    FOREIGN KEY (genre_id)  REFERENCES genre(genre_id)  ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
-- PERSON  +  MOVIE_CAST  +  MOVIE_CREW
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS person (
    person_id            BIGINT          PRIMARY KEY,
    name                 VARCHAR(255)    NOT NULL,
    original_name        VARCHAR(255),
    -- 0=Unknown, 1=Female, 2=Male, 3=Non-binary/Other (TMDB occasionally uses 3)
    gender               INT             CHECK (gender IN (0, 1, 2, 3) OR gender IS NULL),
    known_for_department VARCHAR(100),
    profile_path         VARCHAR(255),
    popularity           DECIMAL(12, 4)
);

-- credit_id is part of the PK so an actor with multiple roles in one movie
-- (e.g. voice cast + on-screen) gets a separate row per credit
CREATE TABLE IF NOT EXISTS movie_cast (
    movie_id        BIGINT          NOT NULL,
    person_id       BIGINT          NOT NULL,
    credit_id       VARCHAR(64)     NOT NULL,
    character_name  TEXT,
    cast_order      INT,
    cast_id         INT,
    PRIMARY KEY (movie_id, person_id, credit_id),
    FOREIGN KEY (movie_id)   REFERENCES movie(movie_id)   ON DELETE CASCADE,
    FOREIGN KEY (person_id)  REFERENCES person(person_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS movie_crew (
    movie_id    BIGINT          NOT NULL,
    person_id   BIGINT          NOT NULL,
    credit_id   VARCHAR(64)     NOT NULL,
    department  VARCHAR(255),
    job_title   VARCHAR(255)    NOT NULL,
    PRIMARY KEY (movie_id, person_id, credit_id),
    FOREIGN KEY (movie_id)   REFERENCES movie(movie_id)   ON DELETE CASCADE,
    FOREIGN KEY (person_id)  REFERENCES person(person_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
-- KEYWORD  +  MOVIE_KEYWORD  (M:N)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS keyword (
    keyword_id      BIGINT          PRIMARY KEY,
    keyword_name    VARCHAR(255)    NOT NULL UNIQUE  -- keyword names are globally unique
);

CREATE TABLE IF NOT EXISTS movie_keyword (
    movie_id    BIGINT  NOT NULL,
    keyword_id  BIGINT  NOT NULL,
    PRIMARY KEY (movie_id, keyword_id),
    FOREIGN KEY (movie_id)    REFERENCES movie(movie_id)     ON DELETE CASCADE,
    FOREIGN KEY (keyword_id)  REFERENCES keyword(keyword_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
-- COMPANY  +  MOVIE_COMPANY  (M:N)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company (
    company_id      BIGINT          PRIMARY KEY,
    company_name    VARCHAR(255)    NOT NULL,
    logo_path       VARCHAR(255),
    origin_country  VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS movie_company (
    movie_id    BIGINT  NOT NULL,
    company_id  BIGINT  NOT NULL,
    PRIMARY KEY (movie_id, company_id),
    FOREIGN KEY (movie_id)   REFERENCES movie(movie_id)     ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES company(company_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
-- COUNTRY  +  MOVIE_COUNTRY  (M:N)  — from production_countries API field
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS country (
    country_code    VARCHAR(10)     PRIMARY KEY,    -- ISO 3166-1 alpha-2 e.g. "US"
    country_name    VARCHAR(255)    NOT NULL
);

CREATE TABLE IF NOT EXISTS movie_country (
    movie_id        BIGINT      NOT NULL,
    country_code    VARCHAR(10) NOT NULL,
    PRIMARY KEY (movie_id, country_code),
    FOREIGN KEY (movie_id)      REFERENCES movie(movie_id)       ON DELETE CASCADE,
    FOREIGN KEY (country_code)  REFERENCES country(country_code) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
-- REVIEW
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review (
    review_id           VARCHAR(128)    PRIMARY KEY,
    movie_id            BIGINT          NOT NULL,
    author_name         VARCHAR(255),
    author_username     VARCHAR(255),
    author_display_name VARCHAR(255),
    author_avatar_path  VARCHAR(255),
    author_rating       DECIMAL(4, 1),
    content             TEXT            NOT NULL,
    created_at          TIMESTAMP,
    updated_at          TIMESTAMP,
    review_url          TEXT,
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
-- TMDB_ACCOUNT  (lightweight external user — no password column)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tmdb_account (
    account_id      BIGINT          PRIMARY KEY,
    username        VARCHAR(255),
    display_name    VARCHAR(255),
    include_adult   BOOLEAN,
    avatar_path     VARCHAR(255)
);

-- ---------------------------------------------------------------------------
-- GUEST_SESSION
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS guest_session (
    guest_session_id    VARCHAR(255)    PRIMARY KEY,
    expires_at          TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- USER_RATING  (from authenticated TMDB accounts)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_rating (
    account_id      BIGINT          NOT NULL,
    movie_id        BIGINT          NOT NULL,
    rating_value    DECIMAL(3, 1)   NOT NULL,
    created_at      TIMESTAMP,
    PRIMARY KEY (account_id, movie_id),
    FOREIGN KEY (account_id) REFERENCES tmdb_account(account_id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id)   REFERENCES movie(movie_id)           ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
-- GUEST_RATING  (from guest sessions)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS guest_rating (
    guest_session_id    VARCHAR(255)    NOT NULL,
    movie_id            BIGINT          NOT NULL,
    rating_value        DECIMAL(3, 1)   NOT NULL,
    created_at          TIMESTAMP,
    PRIMARY KEY (guest_session_id, movie_id),
    FOREIGN KEY (guest_session_id) REFERENCES guest_session(guest_session_id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id)         REFERENCES movie(movie_id)                  ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
-- Indexes for common query patterns
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_movie_release_date    ON movie(release_date);
CREATE INDEX IF NOT EXISTS idx_movie_popularity      ON movie(popularity DESC);
CREATE INDEX IF NOT EXISTS idx_movie_vote_average    ON movie(vote_average DESC);
CREATE INDEX IF NOT EXISTS idx_review_movie_id       ON review(movie_id);
CREATE INDEX IF NOT EXISTS idx_movie_cast_person_id  ON movie_cast(person_id);
CREATE INDEX IF NOT EXISTS idx_movie_crew_person_id  ON movie_crew(person_id);
CREATE INDEX IF NOT EXISTS idx_movie_keyword_kw_id   ON movie_keyword(keyword_id);
