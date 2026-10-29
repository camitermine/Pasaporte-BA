-- Esquema de desarrollo de Pasaporte BA.
-- MySQL conserva los datos maestros y transaccionales. HBase se usa como
-- proyeccion optimizada de la actividad (historiales, pasaporte y rankings).

DROP TABLE IF EXISTS sesion;
DROP TABLE IF EXISTS favorito;
DROP TABLE IF EXISTS sugerencia_lugar;
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
    nombre       VARCHAR(80) NOT NULL,
    id_tipo      TINYINT UNSIGNED NOT NULL,
    UNIQUE (nombre, id_tipo),
    FOREIGN KEY (id_tipo) REFERENCES tipo_lugar (id_tipo)
);

CREATE TABLE fuente (
    id_fuente      TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(100) NOT NULL UNIQUE,
    url            VARCHAR(500),
    fecha_descarga DATE
);

CREATE TABLE lugar (
    id_lugar        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre          VARCHAR(200) NOT NULL,
    direccion       VARCHAR(200),
    latitud         DECIMAL(10, 7),
    longitud        DECIMAL(10, 7),
    id_categoria    SMALLINT UNSIGNED NOT NULL,
    id_barrio       SMALLINT UNSIGNED NULL,
    id_fuente       TINYINT UNSIGNED NULL,
    id_origen       VARCHAR(80) NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_alta      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE (id_fuente, id_origen),
    INDEX idx_lugar_ubicacion (latitud, longitud),
    INDEX idx_lugar_filtros (activo, id_barrio, id_categoria),
    FOREIGN KEY (id_categoria) REFERENCES categoria (id_categoria),
    FOREIGN KEY (id_barrio) REFERENCES barrio (id_barrio),
    FOREIGN KEY (id_fuente) REFERENCES fuente (id_fuente)
);

CREATE TABLE usuario (
    id_usuario      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre_usuario  VARCHAR(30) NOT NULL UNIQUE,
    nombre          VARCHAR(100) NOT NULL,
    email           VARCHAR(120) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    rol             ENUM('usuario', 'admin') NOT NULL DEFAULT 'usuario',
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    id_barrio       SMALLINT UNSIGNED NULL,
    fecha_alta      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_barrio) REFERENCES barrio (id_barrio)
);

CREATE TABLE checkin (
    id_checkin  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario  INT UNSIGNED NOT NULL,
    id_lugar    INT UNSIGNED NOT NULL,
    fecha_hora  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    puntaje     TINYINT UNSIGNED NULL CHECK (puntaje BETWEEN 1 AND 5),
    comentario  VARCHAR(280) NULL,
    verificado  BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_checkin_lugar_fecha (id_lugar, fecha_hora),
    INDEX idx_checkin_usuario_fecha (id_usuario, fecha_hora),
    FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario) ON DELETE RESTRICT,
    FOREIGN KEY (id_lugar) REFERENCES lugar (id_lugar) ON DELETE RESTRICT
);

CREATE TABLE favorito (
    id_usuario INT UNSIGNED NOT NULL,
    id_lugar   INT UNSIGNED NOT NULL,
    fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_usuario, id_lugar),
    FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_lugar) REFERENCES lugar (id_lugar) ON DELETE CASCADE
);

CREATE TABLE sugerencia_lugar (
    id_sugerencia BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario    INT UNSIGNED NOT NULL,
    nombre        VARCHAR(200) NOT NULL,
    direccion     VARCHAR(200),
    latitud       DECIMAL(10, 7),
    longitud      DECIMAL(10, 7),
    id_categoria  SMALLINT UNSIGNED NOT NULL,
    id_barrio     SMALLINT UNSIGNED NULL,
    comentario    VARCHAR(500),
    estado        ENUM('pendiente', 'aprobada', 'rechazada') NOT NULL DEFAULT 'pendiente',
    fecha_alta    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_revisor    INT UNSIGNED NULL,
    fecha_revision DATETIME NULL,
    motivo_revision VARCHAR(500) NULL,
    id_lugar_creado INT UNSIGNED NULL,
    INDEX idx_sugerencia_estado_fecha (estado, fecha_alta),
    FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario) ON DELETE RESTRICT,
    FOREIGN KEY (id_revisor) REFERENCES usuario (id_usuario) ON DELETE RESTRICT,
    FOREIGN KEY (id_categoria) REFERENCES categoria (id_categoria),
    FOREIGN KEY (id_barrio) REFERENCES barrio (id_barrio),
    FOREIGN KEY (id_lugar_creado) REFERENCES lugar (id_lugar) ON DELETE SET NULL
);

CREATE TABLE sesion (
    id_sesion   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario  INT UNSIGNED NOT NULL,
    token_hash  CHAR(64) NOT NULL UNIQUE,
    fecha_alta  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion DATETIME NOT NULL,
    revocada    BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_sesion_usuario (id_usuario, revocada),
    FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario) ON DELETE CASCADE
);
