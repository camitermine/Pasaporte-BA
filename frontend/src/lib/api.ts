// Cliente HTTP del backend. Agrega la sesion y registra que motor resolvio cada pedido.

import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useConfig } from './config';
import type { Meta, Pagina } from './tipos';

export class ApiError extends Error {
  constructor(mensaje: string, public status: number, public meta: Meta | null) {
    super(mensaje);
  }
}

function mensajeDe(json: any, status: number): string {
  if (typeof json?.error === 'string') return json.error;
  if (typeof json?.detail === 'string') return json.detail;
  if (Array.isArray(json?.detail)) {
    // Errores de validación de FastAPI
    return json.detail.map((d: any) => `${d.loc?.slice(-1)[0] ?? ''}: ${d.msg}`).join('\n');
  }
  return `Error ${status}`;
}

export function mensajeError(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export function useApi() {
  const { apiUrl, token, limpiarSesion, registrarMeta } = useConfig();

  return useMemo(() => {
    async function pedir<T>(metodo: string, ruta: string, cuerpo?: unknown): Promise<T> {
      const controlador = new AbortController();
      const timeout = setTimeout(() => controlador.abort(), 15000);
      let resp: Response;
      try {
        resp = await fetch(apiUrl.replace(/\/$/, '') + ruta, {
          method: metodo,
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
          signal: controlador.signal,
        });
      } catch {
        throw new ApiError(`No se pudo conectar con el backend (${apiUrl}). Revisá la URL en Ajustes.`, 0, null);
      } finally {
        clearTimeout(timeout);
      }
      let json: any = null;
      try {
        json = await resp.json();
      } catch {
        // respuesta sin cuerpo JSON
      }
      if (json?.meta) registrarMeta(json.meta, `${metodo} ${ruta}`);
      if (!resp.ok) {
        if (resp.status === 401 && token) limpiarSesion();
        throw new ApiError(mensajeDe(json, resp.status), resp.status, json?.meta ?? null);
      }
      return json.data as T;
    }

    return {
      get: <T>(ruta: string) => pedir<T>('GET', ruta),
      post: <T>(ruta: string, cuerpo: unknown) => pedir<T>('POST', ruta, cuerpo),
      put: <T>(ruta: string, cuerpo: unknown) => pedir<T>('PUT', ruta, cuerpo),
      del: <T>(ruta: string) => pedir<T>('DELETE', ruta),
    };
  }, [apiUrl, token, limpiarSesion, registrarMeta]);
}

/** Construye un query string ignorando valores vacíos. */
export function qs(params: Record<string, string | number | null | undefined>): string {
  const partes = Object.entries(params)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`);
  return partes.length ? `?${partes.join('&')}` : '';
}

/** Carga datos al enfocar la pantalla y cada vez que cambian las dependencias o el motor. */
export function useCarga<T>(fn: () => Promise<T>, deps: unknown[]) {
  const { token, apiUrl } = useConfig();
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const fnRef = useRef(fn);
  useEffect(() => { fnRef.current = fn; }, [fn]);
  const depsKey = JSON.stringify(deps);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setDatos(await fnRef.current());
    } catch (e) {
      setError(mensajeError(e));
    } finally {
      setCargando(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      recargar();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [recargar, token, apiUrl, depsKey]),
  );

  return { datos, error, cargando, recargar };
}

/** Listado paginado por cursor (el cursor lo arma cada motor; para la app es opaco). */
export function usePaginado<T>(ruta: (cursor: string | null) => string, deps: unknown[]) {
  const api = useApi();
  const { token, apiUrl } = useConfig();
  const [items, setItems] = useState<T[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const rutaRef = useRef(ruta);
  useEffect(() => { rutaRef.current = ruta; }, [ruta]);
  const pedidoActual = useRef(0);
  const depsKey = JSON.stringify(deps);

  const cargar = useCallback(
    async (desde: string | null) => {
      const pedido = ++pedidoActual.current;
      setCargando(true);
      setError(null);
      try {
        const pagina = await api.get<Pagina<T>>(rutaRef.current(desde));
        if (pedido !== pedidoActual.current) return; // llegó tarde: ya hay otra búsqueda
        setItems((prev) => (desde ? [...prev, ...pagina.items] : pagina.items));
        setCursor(pagina.siguiente_cursor);
      } catch (e) {
        if (pedido === pedidoActual.current) setError(mensajeError(e));
      } finally {
        if (pedido === pedidoActual.current) setCargando(false);
      }
    },
    [api],
  );

  useFocusEffect(
    useCallback(() => {
      cargar(null);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [cargar, token, apiUrl, depsKey]),
  );

  return {
    items,
    error,
    cargando,
    hayMas: cursor !== null,
    cargarMas: () => {
      if (cursor && !cargando) cargar(cursor);
    },
    recargar: () => cargar(null),
  };
}

/** Vuelve a la pantalla anterior; si no hay (se entró directo por URL), va a la ruta indicada. */
export function volver(alternativa: string) {
  if (router.canGoBack()) router.back();
  else router.replace(alternativa as any);
}
