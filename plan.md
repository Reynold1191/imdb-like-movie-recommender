**TMDB Movie Recommendation Database Design  
(Revised HW2-style Document)**

_Scope: movie-centered schema using TMDB movie details, credits, reviews, keywords, account ratings, and guest ratings.  
_

# 1\. Design Scope and Key Assumptions

**Goal.** Design a relational schema for a movie recommendation / catalog application whose data is collected from the TMDB API. The schema is movie-centered and stores metadata, genres, cast/crew people, keywords, companies, reviews, and rating activity.

**Important design choice.** This schema stores **TMDB_ACCOUNT** as a lightweight external-user entity, not as a full local authentication table. Therefore there is no password column. TMDB handles authentication externally, while this database stores only the account information and rating behavior that the API exposes.

**Keyword note.** Each movie can have multiple keywords. In practice, after a movie ID is discovered, the application can retrieve keyword data either with _GET /movie/{movie_id}/keywords_ or by using append-to-response in the details workflow when supported by the implementation. Because keywords are multivalued and reused across movies, they should be normalized into **KEYWORD** and **MOVIE_KEYWORD**.

# 2\. Final Relations

- MOVIE(movieID PK, title, originalTitle, overview, releaseDate, runtime, originalLanguage, status, imdbID, popularity, voteAverage, voteCount, adultFlag, videoFlag, posterPath, backdropPath, homepage, tagline, budget, revenue, collectionID NULL, collectionName NULL)
- GENRE(genreID PK, genreName)
- MOVIE_GENRE(movieID PK/FK -> MOVIE.movieID, genreID PK/FK -> GENRE.genreID)
- PERSON(personID PK, name, originalName, gender, knownForDepartment, profilePath, popularity)
- MOVIE_CAST(movieID PK/FK -> MOVIE.movieID, personID PK/FK -> PERSON.personID, characterName, castOrder, creditID, castID NULL)
- MOVIE_CREW(movieID PK/FK -> MOVIE.movieID, personID PK/FK -> PERSON.personID, department, jobTitle, creditID)
- KEYWORD(keywordID PK, keywordName)
- MOVIE_KEYWORD(movieID PK/FK -> MOVIE.movieID, keywordID PK/FK -> KEYWORD.keywordID)
- COMPANY(companyID PK, companyName, logoPath, originCountry)
- MOVIE_COMPANY(movieID PK/FK -> MOVIE.movieID, companyID PK/FK -> COMPANY.companyID)
- TMDB_ACCOUNT(accountID PK, username, displayName, includeAdult, avatarPath)
- GUEST_SESSION(guestSessionID PK, expiresAt)
- REVIEW(reviewID PK, movieID FK -> MOVIE.movieID, authorName, authorUsername, authorDisplayName, authorAvatarPath, authorRating NULL, content, createdAt, updatedAt, reviewURL)
- USER_RATING(accountID PK/FK -> TMDB_ACCOUNT.accountID, movieID PK/FK -> MOVIE.movieID, ratingValue, createdAt)
- GUEST_RATING(guestSessionID PK/FK -> GUEST_SESSION.guestSessionID, movieID PK/FK -> MOVIE.movieID, ratingValue, createdAt)

# 3\. Meaning of Each Table

| Relation      | Meaning / Purpose                                                                                                                                                                                                                       |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MOVIE         | Stores one row per movie returned by TMDB. This is the core entity that everything else connects to. Movie-level attributes such as title, release date, runtime, popularity, voteAverage, and voteCount describe the movie as a whole. |
| GENRE         | Stores the master list of genres such as Action, Adventure, or Science Fiction. A genre is reusable across many movies.                                                                                                                 |
| MOVIE_GENRE   | Bridge table that resolves the many-to-many relationship between MOVIE and GENRE. A movie can have many genres and a genre can belong to many movies.                                                                                   |
| PERSON        | Stores unique people appearing in credits. This includes actors in cast and staff in crew, such as directors, producers, writers, and composers.                                                                                        |
| MOVIE_CAST    | Stores cast-specific participation of a person in a movie, including the role name, cast order, and credit identifiers. The same person can appear in many different movies.                                                            |
| MOVIE_CREW    | Stores crew-specific participation of a person in a movie, including department and job title. This separates movie-specific crew roles from the reusable person profile.                                                               |
| KEYWORD       | Stores unique TMDB keywords such as 'empire', 'galaxy', or 'rebellion'. Keywords are descriptive tags that help recommendation, filtering, or thematic search.                                                                          |
| MOVIE_KEYWORD | Bridge table between MOVIE and KEYWORD. Each movie may have many keywords, and the same keyword may be attached to many movies.                                                                                                         |
| COMPANY       | Stores production companies such as Lucasfilm Ltd. and 20th Century Fox. Company attributes are reusable across movies.                                                                                                                 |
| MOVIE_COMPANY | Bridge table between MOVIE and COMPANY because one movie can have multiple production companies and one company can participate in multiple movies.                                                                                     |
| TMDB_ACCOUNT  | Stores external TMDB account identity used for account-based rating retrieval. It is intentionally lightweight and does not store passwords because authentication is managed by TMDB, not by this local schema.                        |
| GUEST_SESSION | Stores TMDB guest session identifiers and expiration time. This supports anonymous or guest rating flows provided by the API.                                                                                                           |
| REVIEW        | Stores review events attached to one movie. Review-level metadata such as author snapshot, content, timestamps, and optional author rating are stored because TMDB returns them inside each review payload.                             |
| USER_RATING   | Stores ratings made by a TMDB account for a movie. One account can rate many movies, and each movie can be rated by many accounts.                                                                                                      |
| GUEST_RATING  | Stores ratings submitted with a guest session instead of a permanent TMDB account. This table is separate because guestSessionID and accountID belong to different identity domains.                                                    |

# 4\. Why PERSON, KEYWORD, and COMPANY Must Exist

- PERSON is needed because cast and crew entries are not just plain text labels. TMDB returns stable person IDs and reusable profile attributes. If person data were stored directly in MOVIE_CAST and MOVIE_CREW only, person profiles would be duplicated every time the same actor or crew member appears in another movie.
- KEYWORD is needed because each movie can have many keyword objects. In the Star Wars example, the JSON contains a keywords object with an array of keyword rows such as 'empire', 'galaxy', 'rebellion', and 'android'. A normalized design stores each keyword once in KEYWORD and uses MOVIE_KEYWORD to associate movies with keywords.
- COMPANY is needed because production companies are also reusable entities. A company can appear in many movies, so company data should not be duplicated inside the movie table.

# 5\. API Mapping: How to Populate Each Relation

**Workflow summary.** A common TMDB workflow is: first discover or search for a movie ID, then query movie details, then enrich the movie with credits, keywords, reviews, and rating data as needed.

| Relation      | TMDB API Endpoint(s)                                                                     | How it is used                                                                    |
| ------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| MOVIE         | GET /discover/movie and GET /movie/{movie_id}                                            | discover gives candidate movie IDs; movie details populates core movie attributes |
| GENRE         | GET /genre/movie/list or genres array from GET /movie/{movie_id}                         | load reference genres once or extract per movie                                   |
| MOVIE_GENRE   | GET /movie/{movie_id}                                                                    | use the genres array inside movie details                                         |
| PERSON        | GET /movie/{movie_id}/credits                                                            | use cast and crew arrays to create or update people                               |
| MOVIE_CAST    | GET /movie/{movie_id}/credits                                                            | use cast array fields such as character, order, cast_id, credit_id                |
| MOVIE_CREW    | GET /movie/{movie_id}/credits                                                            | use crew array fields such as department, job, credit_id                          |
| KEYWORD       | GET /movie/{movie_id}/keywords                                                           | create or update one row per keyword object                                       |
| MOVIE_KEYWORD | GET /movie/{movie_id}/keywords                                                           | bridge each movie_id to each keyword id returned                                  |
| COMPANY       | GET /movie/{movie_id}                                                                    | use production_companies array                                                    |
| MOVIE_COMPANY | GET /movie/{movie_id}                                                                    | bridge each movie_id to each production company id returned                       |
| TMDB_ACCOUNT  | GET /account/{account_id}                                                                | retrieve public account details after account identity is known                   |
| GUEST_SESSION | GET /authentication/guest_session/new                                                    | store guest_session_id and expires_at                                             |
| REVIEW        | GET /movie/{movie_id}/reviews                                                            | use review id, content, author snapshot, timestamps, and URL                      |
| USER_RATING   | GET /account/{account_id}/rated/movies and POST /movie/{movie_id}/rating with session_id | retrieve or persist account-based ratings                                         |
| GUEST_RATING  | POST /movie/{movie_id}/rating with guest_session_id                                      | persist guest ratings tied to guest session                                       |

Practical extraction note for keywords: if a movie JSON already contains a nested keywords object with a keywords array, that payload is enough to populate both KEYWORD and MOVIE_KEYWORD. In other words, once a movie is fetched, keyword data can be normalized immediately instead of being left as raw nested JSON.

# 6\. Relation Mapping Choices

- MOVIE is the central entity because all requested application behavior is movie-centered.
- GENRE, KEYWORD, COMPANY, and PERSON are modeled as independent entity sets because they are reusable across many movies.
- MOVIE_GENRE, MOVIE_KEYWORD, and MOVIE_COMPANY are associative relations that resolve many-to-many relationships.
- PERSON is separated from MOVIE_CAST and MOVIE_CREW so that reusable profile attributes are stored once while movie-specific role attributes are stored in the bridge tables.
- REVIEW stores author fields as a snapshot inside the review relation because the review payload already nests author details and TMDB does not expose a full public user model suitable for a separate normalized USER table here.
- USER_RATING and GUEST_RATING are intentionally split. Although both represent ratings, their identifiers come from different domains (accountID vs guestSessionID). Merging them into one table would either require nullable foreign keys or a more abstract supertype not directly supported by the TMDB workflow.
- TMDB_ACCOUNT is treated as a lightweight user-like entity for testing and integration. It is not a local authentication table and therefore has no password.

# 7\. Functional Dependencies

| Relation      | Relevant FD(s)                                                                                                                               | Justification                                                 |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| MOVIE         | movieID -> all non-key movie attributes                                                                                                      | movieID uniquely identifies each movie                        |
| GENRE         | genreID -> genreName                                                                                                                         | genre ID determines its name                                  |
| MOVIE_GENRE   | (movieID, genreID) -> no non-key attributes                                                                                                  | pure associative relation                                     |
| PERSON        | personID -> name, originalName, gender, knownForDepartment, profilePath, popularity                                                          | person ID uniquely identifies a person                        |
| MOVIE_CAST    | (movieID, personID) -> characterName, castOrder, creditID, castID                                                                            | one cast row per movie-person participation under this design |
| MOVIE_CREW    | (movieID, personID, creditID) -> department, jobTitle                                                                                        | creditID distinguishes crew participations when needed        |
| KEYWORD       | keywordID -> keywordName                                                                                                                     | keyword ID determines keyword text                            |
| MOVIE_KEYWORD | (movieID, keywordID) -> no non-key attributes                                                                                                | pure associative relation                                     |
| COMPANY       | companyID -> companyName, logoPath, originCountry                                                                                            | company ID determines company attributes                      |
| MOVIE_COMPANY | (movieID, companyID) -> no non-key attributes                                                                                                | pure associative relation                                     |
| TMDB_ACCOUNT  | accountID -> username, displayName, includeAdult, avatarPath                                                                                 | TMDB account ID determines exposed account attributes         |
| GUEST_SESSION | guestSessionID -> expiresAt                                                                                                                  | guest session ID determines expiration                        |
| REVIEW        | reviewID -> movieID, authorName, authorUsername, authorDisplayName, authorAvatarPath, authorRating, content, createdAt, updatedAt, reviewURL | reviewID uniquely identifies each review                      |
| USER_RATING   | (accountID, movieID) -> ratingValue, createdAt                                                                                               | one account rating per movie                                  |
| GUEST_RATING  | (guestSessionID, movieID) -> ratingValue, createdAt                                                                                          | one guest-session rating per movie                            |

# 8\. Normalization Discussion

- MOVIE, GENRE, PERSON, KEYWORD, COMPANY, TMDB_ACCOUNT, and GUEST_SESSION are in BCNF because each non-trivial determinant is the relation's key.
- Pure bridge tables such as MOVIE_GENRE, MOVIE_KEYWORD, and MOVIE_COMPANY are in BCNF because they contain only key attributes.
- MOVIE_CAST and MOVIE_CREW keep reusable person attributes outside the bridge tables, so the design avoids repeating person profile data for every movie appearance.
- REVIEW is treated as an event/entity relation with reviewID as determinant. Author-related values are stored as review-level snapshots because that is how the API returns them.
- USER_RATING and GUEST_RATING are split rather than merged, which avoids null-heavy design and keeps each relation tied to one identity domain.
- Under these assumptions, the stored schema is well normalized through BCNF. Behavioral concerns such as pagination, API authentication, or whether a crew member can have multiple jobs on one movie are application-level considerations rather than normalization defects.

# 9\. PostgreSQL CREATE TABLE Statements

CREATE TABLE movie (  
movie_id BIGINT PRIMARY KEY,  
title VARCHAR(255) NOT NULL,  
original_title VARCHAR(255),  
overview TEXT,  
release_date DATE,  
runtime INT,  
original_language VARCHAR(10),  
status VARCHAR(50),  
imdb_id VARCHAR(20),  
popularity DECIMAL(12,4),  
vote_average DECIMAL(4,3),  
vote_count INT,  
adult_flag BOOLEAN,  
video_flag BOOLEAN,  
poster_path VARCHAR(255),  
backdrop_path VARCHAR(255),  
homepage TEXT,  
tagline TEXT,  
budget BIGINT,  
revenue BIGINT,  
collection_id BIGINT,  
collection_name VARCHAR(255)  
);

CREATE TABLE genre (  
genre_id INT PRIMARY KEY,  
genre_name VARCHAR(100) NOT NULL  
);  
<br/>CREATE TABLE movie_genre (  
movie_id BIGINT NOT NULL,  
genre_id INT NOT NULL,  
PRIMARY KEY (movie_id, genre_id),  
FOREIGN KEY (movie_id) REFERENCES movie(movie_id),  
FOREIGN KEY (genre_id) REFERENCES genre(genre_id)  
);

CREATE TABLE person (  
person_id BIGINT PRIMARY KEY,  
name VARCHAR(255) NOT NULL,  
original_name VARCHAR(255),  
gender INT,  
known_for_department VARCHAR(100),  
profile_path VARCHAR(255),  
popularity DECIMAL(12,4)  
);  
<br/>CREATE TABLE movie_cast (  
movie_id BIGINT NOT NULL,  
person_id BIGINT NOT NULL,  
character_name VARCHAR(255),  
cast_order INT,  
credit_id VARCHAR(64),  
cast_id INT,  
PRIMARY KEY (movie_id, person_id),  
FOREIGN KEY (movie_id) REFERENCES movie(movie_id),  
FOREIGN KEY (person_id) REFERENCES person(person_id)  
);  
<br/>CREATE TABLE movie_crew (  
movie_id BIGINT NOT NULL,  
person_id BIGINT NOT NULL,  
credit_id VARCHAR(64) NOT NULL,  
department VARCHAR(255),  
job_title VARCHAR(255) NOT NULL,  
PRIMARY KEY (movie_id, person_id, credit_id),  
FOREIGN KEY (movie_id) REFERENCES movie(movie_id),  
FOREIGN KEY (person_id) REFERENCES person(person_id)  
);

CREATE TABLE keyword (  
keyword_id BIGINT PRIMARY KEY,  
keyword_name VARCHAR(255) NOT NULL  
);  
<br/>CREATE TABLE movie_keyword (  
movie_id BIGINT NOT NULL,  
keyword_id BIGINT NOT NULL,  
PRIMARY KEY (movie_id, keyword_id),  
FOREIGN KEY (movie_id) REFERENCES movie(movie_id),  
FOREIGN KEY (keyword_id) REFERENCES keyword(keyword_id)  
);

CREATE TABLE company (  
company_id BIGINT PRIMARY KEY,  
company_name VARCHAR(255) NOT NULL,  
logo_path VARCHAR(255),  
origin_country VARCHAR(10)  
);  
<br/>CREATE TABLE movie_company (  
movie_id BIGINT NOT NULL,  
company_id BIGINT NOT NULL,  
PRIMARY KEY (movie_id, company_id),  
FOREIGN KEY (movie_id) REFERENCES movie(movie_id),  
FOREIGN KEY (company_id) REFERENCES company(company_id)  
);

CREATE TABLE tmdb_account (  
account_id BIGINT PRIMARY KEY,  
username VARCHAR(255),  
display_name VARCHAR(255),  
include_adult BOOLEAN,  
avatar_path VARCHAR(255)  
);  
<br/>CREATE TABLE guest_session (  
guest_session_id VARCHAR(255) PRIMARY KEY,  
expires_at TIMESTAMP  
);

CREATE TABLE review (  
review_id VARCHAR(128) PRIMARY KEY,  
movie_id BIGINT NOT NULL,  
author_name VARCHAR(255),  
author_username VARCHAR(255),  
author_display_name VARCHAR(255),  
author_avatar_path VARCHAR(255),  
author_rating DECIMAL(4,1),  
content TEXT NOT NULL,  
created_at TIMESTAMP,  
updated_at TIMESTAMP,  
review_url TEXT,  
FOREIGN KEY (movie_id) REFERENCES movie(movie_id)  
);

CREATE TABLE user_rating (  
account_id BIGINT NOT NULL,  
movie_id BIGINT NOT NULL,  
rating_value DECIMAL(3,1) NOT NULL,  
created_at TIMESTAMP,  
PRIMARY KEY (account_id, movie_id),  
FOREIGN KEY (account_id) REFERENCES tmdb_account(account_id),  
FOREIGN KEY (movie_id) REFERENCES movie(movie_id)  
);  
<br/>CREATE TABLE guest_rating (  
guest_session_id VARCHAR(255) NOT NULL,  
movie_id BIGINT NOT NULL,  
rating_value DECIMAL(3,1) NOT NULL,  
created_at TIMESTAMP,  
PRIMARY KEY (guest_session_id, movie_id),  
FOREIGN KEY (guest_session_id) REFERENCES guest_session(guest_session_id),  
FOREIGN KEY (movie_id) REFERENCES movie(movie_id)  
);

# 10\. Final Relation Table Diagram

MOVIE  
|--&lt; MOVIE_GENRE &gt;-- GENRE  
|--&lt; MOVIE_CAST &gt;-- PERSON  
|--&lt; MOVIE_CREW &gt;-- PERSON  
|--&lt; MOVIE_KEYWORD &gt;-- KEYWORD  
|--&lt; MOVIE_COMPANY &gt;-- COMPANY  
|--< REVIEW  
|--&lt; USER_RATING &gt;-- TMDB_ACCOUNT  
|--&lt; GUEST_RATING &gt;-- GUEST_SESSION

Interpretation: MOVIE is the hub relation. Reusable reference entities (GENRE, PERSON, KEYWORD, COMPANY) are linked by bridge tables. REVIEW is a movie-owned entity, while USER_RATING and GUEST_RATING connect MOVIE to two different rating identity sources.

# 11\. Short Discussion / Justification

- This revised schema is more complete than a movie-only schema because it explicitly models people, keywords, and production companies as reusable entity sets instead of leaving them embedded inside JSON blobs.
- Adding KEYWORD and MOVIE_KEYWORD is important because every fetched movie may already contain keyword objects in the returned payload, and recommendations often benefit from thematic tags in addition to genres.
- Separating PERSON from MOVIE_CAST and MOVIE_CREW avoids duplication and supports future extensions such as a PEOPLE search page, actor filmography, or crew analytics.
- TMDB_ACCOUNT is intentionally minimal. It is sufficient for integration tests and prototype personalization, but a full production system with local login/logout would add a separate APP_USER table with password_hash and session management.
- Overall, the schema is normalized, closely aligned with the TMDB API, and ready for ETL from raw movie JSON into structured PostgreSQL tables.