// Espejo de los modelos de dominio del backend (backend/app/dominio.py).

export type Motor = 'mysql' | 'hbase';

export interface Operacion {
  op: string;
  ms: number;
}

export interface Meta {
  motor: Motor;
  duracion_ms: number;
  operaciones: Operacion[];
}

export interface Barrio {
  id: number;
  nombre: string;
  comuna: number;
}

export interface Categoria {
  id: number;
  nombre: string;
  tipo: string;
}

export interface Ref {
  id: number;
  nombre: string;
}

export interface Lugar {
  id: number;
  nombre: string;
  direccion: string | null;
  latitud: number | null;
  longitud: number | null;
  categoria: Categoria;
  barrio: Barrio | null;
  fuente: string | null;
  activo: boolean;
}

export interface LugarIn {
  nombre: string;
  direccion: string | null;
  latitud: number | null;
  longitud: number | null;
  id_categoria: number;
  id_barrio: number | null;
}

export interface LugarCercano {
  lugar: Lugar;
  distancia_m: number;
}

export interface Usuario {
  id: number;
  nombre_usuario: string;
  nombre: string;
  email: string;
  barrio: Barrio | null;
  fecha_alta: string;
  rol: 'usuario' | 'admin';
  activo: boolean;
}

export interface Sesion {
  token: string;
  usuario: Usuario;
}

export interface Checkin {
  id: number;
  usuario: Ref;
  lugar: Ref;
  fecha_hora: string;
  puntaje: number | null;
  comentario: string | null;
  verificado: boolean;
}

export interface Pagina<T> {
  items: T[];
  siguiente_cursor: string | null;
}

export interface ItemRanking {
  puesto: number;
  lugar: Ref;
  categoria: string;
  checkins: number;
}

export interface Pasaporte {
  usuario: Ref;
  total_checkins: number;
  lugares_distintos: number;
  barrios_visitados: { barrio: Barrio; checkins: number }[];
  barrios_faltantes: Barrio[];
  progreso: number;
}

export interface SugerenciaLugar {
  id: number;
  usuario: Ref;
  nombre: string;
  direccion: string | null;
  latitud: number | null;
  longitud: number | null;
  categoria: Categoria;
  barrio: Barrio | null;
  comentario: string | null;
  estado: 'pendiente' | 'aprobada' | 'rechazada';
  fecha_alta: string;
  revisor: Ref | null;
  fecha_revision: string | null;
  motivo_revision: string | null;
  id_lugar_creado: number | null;
}
