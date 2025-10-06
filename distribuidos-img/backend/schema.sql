-- Esquema base de datos para distribuidos_img

CREATE DATABASE IF NOT EXISTS distribuidos_img CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE distribuidos_img;

CREATE TABLE IF NOT EXISTS usuarios (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    email VARCHAR(120) NOT NULL,
    pass_hash VARCHAR(255) NULL,
    estado ENUM('activo','inactivo','bloqueado') NOT NULL DEFAULT 'activo',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_usuarios_username (username),
    UNIQUE KEY uk_usuarios_email (email)
);

CREATE TABLE IF NOT EXISTS transformaciones (
    id TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(40) NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    UNIQUE KEY uk_transformaciones_codigo (codigo)
);

CREATE TABLE IF NOT EXISTS nodos (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(255) NOT NULL,
    protocolo ENUM('grpc','soap') NOT NULL DEFAULT 'grpc',
    estado ENUM('activo','inactivo','error') NOT NULL DEFAULT 'inactivo',
    ultima_actividad TIMESTAMP NULL DEFAULT NULL,
    UNIQUE KEY uk_nodos_nombre (nombre),
    KEY idx_nodos_estado (estado)
);

CREATE TABLE IF NOT EXISTS solicitudes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usuario_id BIGINT UNSIGNED NOT NULL,
    estado ENUM('pendiente','en_progreso','completada','fallida','cancelada') NOT NULL DEFAULT 'pendiente',
    total_imagenes INT UNSIGNED NOT NULL DEFAULT 0,
    procesadas INT UNSIGNED NOT NULL DEFAULT 0,
    creadas_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizadas_en DATETIME NULL DEFAULT NULL,
    iniciada_en TIMESTAMP NULL DEFAULT NULL,
    finalizada_en TIMESTAMP NULL DEFAULT NULL,
    KEY idx_solicitudes_usuario_estado (usuario_id, estado),
    CONSTRAINT fk_solicitudes_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS imagenes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    solicitud_id BIGINT UNSIGNED NOT NULL,
    nombre VARCHAR(255) NOT NULL DEFAULT '',
    nombre_original VARCHAR(255) NOT NULL,
    ruta_entrada VARCHAR(500) NOT NULL,
    ruta_salida VARCHAR(500) NULL,
    formato_origen ENUM('jpg','jpeg','png','tif','tiff','bmp','gif','webp','otro') NOT NULL DEFAULT 'otro',
    formato_salida ENUM('jpg','png','tif','sin_cambio') NOT NULL DEFAULT 'sin_cambio',
    estado ENUM('pendiente','en_progreso','completada','fallida') NOT NULL DEFAULT 'pendiente',
    nodo_id BIGINT UNSIGNED NULL,
    recibido_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    iniciado_en TIMESTAMP NULL DEFAULT NULL,
    convertido_en TIMESTAMP NULL DEFAULT NULL,
    error TEXT NULL,
    formato_entrada VARCHAR(20) NULL,
    creada_en DATETIME NULL DEFAULT NULL,
    actualizada_en DATETIME NULL DEFAULT NULL,
    KEY idx_imagenes_solicitud (solicitud_id),
    KEY idx_imagenes_estado (estado),
    KEY idx_imagenes_nodo (nodo_id),
    CONSTRAINT fk_imagenes_solicitud FOREIGN KEY (solicitud_id) REFERENCES solicitudes(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_imagenes_nodo FOREIGN KEY (nodo_id) REFERENCES nodos(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS imagen_transformaciones (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    imagen_id BIGINT UNSIGNED NOT NULL,
    transformacion_id TINYINT UNSIGNED NOT NULL,
    orden SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    parametros JSON NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    codigo VARCHAR(50) NOT NULL,
    params_json TEXT NULL,
    creada_en DATETIME NULL DEFAULT NULL,
    KEY idx_imagen_transformaciones (imagen_id, orden),
    KEY idx_transformacion_id (transformacion_id),
    CONSTRAINT fk_img_trans_imagen FOREIGN KEY (imagen_id) REFERENCES imagenes(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_img_trans_transform FOREIGN KEY (transformacion_id) REFERENCES transformaciones(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nivel ENUM('DEBUG','INFO','WARN','ERROR') NOT NULL DEFAULT 'INFO',
    componente VARCHAR(50) NOT NULL,
    nodo_id BIGINT UNSIGNED NULL,
    solicitud_id BIGINT UNSIGNED NULL,
    imagen_id BIGINT UNSIGNED NULL,
    mensaje TEXT NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_logs_nodo (nodo_id),
    KEY idx_logs_solicitud (solicitud_id),
    KEY idx_logs_imagen (imagen_id),
    KEY idx_logs_componente_fecha (componente, creado_en),
    CONSTRAINT fk_logs_nodo FOREIGN KEY (nodo_id) REFERENCES nodos(id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_logs_solicitud FOREIGN KEY (solicitud_id) REFERENCES solicitudes(id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_logs_imagen FOREIGN KEY (imagen_id) REFERENCES imagenes(id) ON DELETE SET NULL ON UPDATE CASCADE
);
