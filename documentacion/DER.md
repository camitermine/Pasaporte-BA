# Diagrama Entidad-Relación — Pasaporte BA

Corresponde exactamente al modelo implementado en `database/mysql/modelo_relacional.sql`.
GitHub y VS Code (con la extensión de Mermaid) lo renderizan directamente. Para el informe,
exportarlo como imagen desde <https://mermaid.live> (pegar el bloque y descargar PNG/SVG) y
guardarlo como `documentacion/DER.png`.

> Notación: pata de gallo (crow's foot). `||` = exactamente uno, `|o` = cero o uno,
> `o{` = cero o muchos. PK = clave primaria, FK = clave foránea, UK = única.

```mermaid
erDiagram
    COMUNA ||--o{ BARRIO : "agrupa"
    TIPO_LUGAR ||--o{ CATEGORIA : "clasifica"
    CATEGORIA ||--o{ LUGAR : "categoriza"
    BARRIO |o--o{ LUGAR : "ubica"
    FUENTE |o--o{ LUGAR : "origina"
    BARRIO |o--o{ USUARIO : "reside"
    USUARIO ||--o{ CHECKIN : "registra"
    LUGAR ||--o{ CHECKIN : "recibe"
    USUARIO ||--o{ FAVORITO : "guarda"
    LUGAR ||--o{ FAVORITO : "es guardado"
    USUARIO ||--o{ SUGERENCIA_LUGAR : "propone"
    USUARIO |o--o{ SUGERENCIA_LUGAR : "revisa"
    CATEGORIA ||--o{ SUGERENCIA_LUGAR : "categoriza"
    BARRIO |o--o{ SUGERENCIA_LUGAR : "ubica"
    LUGAR |o--o| SUGERENCIA_LUGAR : "se crea desde"
    USUARIO ||--o{ SESION : "abre"

    COMUNA {
        tinyint id_comuna PK "1 a 15"
    }
    BARRIO {
        smallint id_barrio PK
        varchar nombre UK
        tinyint id_comuna FK
    }
    TIPO_LUGAR {
        tinyint id_tipo PK
        varchar nombre UK "cultura, patrimonio, arte urbano, gastronomia"
    }
    CATEGORIA {
        smallint id_categoria PK
        varchar nombre "UK junto con id_tipo"
        tinyint id_tipo FK
    }
    FUENTE {
        tinyint id_fuente PK
        varchar nombre UK
        varchar url
        date fecha_descarga
    }
    LUGAR {
        int id_lugar PK
        varchar nombre
        varchar direccion
        decimal latitud
        decimal longitud
        smallint id_categoria FK
        smallint id_barrio FK "nullable"
        tinyint id_fuente FK "nullable"
        varchar id_origen "UK junto con id_fuente"
        boolean activo "baja logica"
        datetime fecha_alta
        datetime fecha_modificacion
    }
    USUARIO {
        int id_usuario PK
        varchar nombre_usuario UK
        varchar nombre
        varchar email UK
        varchar password_hash
        enum rol "usuario o admin"
        boolean activo
        smallint id_barrio FK "nullable"
        datetime fecha_alta
    }
    CHECKIN {
        bigint id_checkin PK
        int id_usuario FK
        int id_lugar FK
        datetime fecha_hora
        tinyint puntaje "1 a 5, nullable"
        varchar comentario "max 280"
        boolean verificado
    }
    FAVORITO {
        int id_usuario PK, FK
        int id_lugar PK, FK
        datetime fecha_alta
    }
    SUGERENCIA_LUGAR {
        bigint id_sugerencia PK
        int id_usuario FK "autor"
        varchar nombre
        varchar direccion
        decimal latitud
        decimal longitud
        smallint id_categoria FK
        smallint id_barrio FK "nullable"
        varchar comentario
        enum estado "pendiente, aprobada, rechazada"
        datetime fecha_alta
        int id_revisor FK "nullable"
        datetime fecha_revision
        varchar motivo_revision
        int id_lugar_creado FK "nullable"
    }
    SESION {
        bigint id_sesion PK
        int id_usuario FK
        char token_hash UK "SHA-256"
        datetime fecha_alta
        datetime fecha_expiracion
        boolean revocada
    }
```

## Cardinalidades explicadas

| Relación | Cardinalidad | Lectura |
|---|---|---|
| Comuna – Barrio | 1 : N | Cada barrio pertenece a una sola comuna; una comuna agrupa varios barrios. |
| Tipo – Categoría | 1 : N | Cada categoría de origen (p. ej. "BAR", "BUSTO") cae en uno de los 4 tipos de la app. |
| Categoría – Lugar | 1 : N | Todo lugar tiene exactamente una categoría. |
| Barrio – Lugar | 0..1 : N | 270 lugares del dataset no tienen barrio validado (`id_barrio` NULL). |
| Fuente – Lugar | 0..1 : N | Los lugares cargados desde la app (por un admin) no tienen fuente. |
| Usuario – Lugar (Check-in) | N : M | Resuelta con la entidad **Check-in**, que tiene atributos propios (fecha, puntaje, comentario). Un usuario puede visitar el mismo lugar varias veces. |
| Usuario – Lugar (Favorito) | N : M | Resuelta con la tabla **Favorito**, PK compuesta: un lugar se guarda una sola vez por usuario. |
| Usuario – Sugerencia | 1 : N (autor) y 0..1 : N (revisor) | Dos relaciones distintas con la misma entidad. |
| Sugerencia – Lugar | 0..1 : 0..1 | Una sugerencia aprobada genera como máximo un lugar. |
| Usuario – Sesión | 1 : N | Sesiones revocables; se guarda solo el hash del token. |
