-- ESQUEMA SOLO PARA DESARROLLO DEL BACKEND.
-- Sigue el borrador de documentacion/DISENO.md (sección 5).
-- El modelo oficial del TP va en database/mysql/modelo_relacional.sql.

DROP TABLE IF EXISTS checkin;
DROP TABLE IF EXISTS usuario;
DROP TABLE IF EXISTS lugar;
DROP TABLE IF EXISTS fuente;
DROP TABLE IF EXISTS categoria;
DROP TABLE IF EXISTS tipo_lugar;
DROP TABLE IF EXISTS barrio;
DROP TABLE IF EXISTS comuna;

CREATE TABLE comuna (
    id_comuna TINYINT UNSIGNED PRIMARY KEY CHECK (id_comuna BETWEEN 1 AND 15)
);

CREATE TABLE barrio (
    id_barrio SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre    VARCHAR(60) NOT NULL UNIQUE,
    id_comuna TINYINT UNSIGNED NOT NULL,
    FOREIGN KEY (id_comuna) REFERENCES comuna (id_comuna)
);

CREATE TABLE tipo_lugar (
    id_tipo TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre  VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE categoria (
    id_categoria SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(60) NOT NULL,
    id_tipo      TINYINT UNSIGNED NOT NULL,
    UNIQUE (nombre, id_tipo),
    FOREIGN KEY (id_tipo) REFERENCES tipo_lugar (id_tipo)
);

CREATE TABLE fuente (
    id_fuente      TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(100) NOT NULL,
    url            VARCHAR(255),
    fecha_descarga DATE
);

CREATE TABLE lugar (
    id_lugar     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(200) NOT NULL,
    direccion    VARCHAR(200),
    latitud      DECIMAL(9, 6),
    longitud     DECIMAL(9, 6),
    id_categoria SMALLINT UNSIGNED NOT NULL,
    id_barrio    SMALLINT UNSIGNED NOT NULL,
    id_fuente    TINYINT UNSIGNED NULL,
    id_origen    VARCHAR(50) NULL,
    UNIQUE (id_fuente, id_origen),
    INDEX (latitud, longitud),
    FOREIGN KEY (id_categoria) REFERENCES categoria (id_categoria),
    FOREIGN KEY (id_barrio) REFERENCES barrio (id_barrio),
    FOREIGN KEY (id_fuente) REFERENCES fuente (id_fuente)
);

CREATE TABLE usuario (
    id_usuario     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre_usuario VARCHAR(30) NOT NULL UNIQUE,
    nombre         VARCHAR(100) NOT NULL,
    email          VARCHAR(120) NOT NULL UNIQUE,
    id_barrio      SMALLINT UNSIGNED NULL,
    fecha_alta     DATETIME NOT NULL,
    FOREIGN KEY (id_barrio) REFERENCES barrio (id_barrio)
);

CREATE TABLE checkin (
    id_checkin BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT UNSIGNED NOT NULL,
    id_lugar   INT UNSIGNED NOT NULL,
    fecha_hora DATETIME NOT NULL,
    puntaje    TINYINT UNSIGNED NULL CHECK (puntaje BETWEEN 1 AND 5),
    comentario VARCHAR(280) NULL,
    INDEX (id_lugar, fecha_hora),
    INDEX (id_usuario, fecha_hora),
    FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario) ON DELETE RESTRICT,
    FOREIGN KEY (id_lugar) REFERENCES lugar (id_lugar) ON DELETE RESTRICT
);
