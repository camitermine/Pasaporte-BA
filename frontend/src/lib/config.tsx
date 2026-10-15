// Configuración global de la app: motor elegido, URL del backend, usuario actual y modo debug.
// Se guarda en el teléfono (AsyncStorage) para que sobreviva a reinicios.

import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Platform } from 'react-native';

import type { Meta, Motor } from './tipos';

const CLAVE = 'pasaporteba:config';

export interface Registro {
  meta: Meta;
  pedido: string; // ej. "GET /lugares?barrio=3"
  hora: Date;
}

interface Persistida {
  apiUrl: string;
  motor: Motor;
  idUsuario: number | null;
  debug: boolean;
}

interface ConfigCtx extends Persistida {
  cambiar: (cambios: Partial<Persistida>) => void;
  historial: Registro[]; // últimas respuestas del backend (para el panel de debug)
  registrarMeta: (meta: Meta, pedido: string) => void;
}

/** En Expo Go el celular se conecta a la PC por la IP de la red local: usamos esa misma IP para el backend. */
function urlPorDefecto(): string {
  if (Platform.OS === 'web') return 'http://localhost:8000';
  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  return host ? `http://${host}:8000` : 'http://192.168.0.17:8000';
}

const Contexto = createContext<ConfigCtx | null>(null);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [cargado, setCargado] = useState(false);
  const [valores, setValores] = useState<Persistida>({
    apiUrl: urlPorDefecto(),
    motor: 'mysql',
    idUsuario: null,
    debug: true,
  });
  const [historial, setHistorial] = useState<Registro[]>([]);

  useEffect(() => {
    AsyncStorage.getItem(CLAVE)
      .then((texto) => {
        if (texto) setValores((v) => ({ ...v, ...JSON.parse(texto) }));
      })
      .catch(() => {})
      .finally(() => setCargado(true));
  }, []);

  const cambiar = useCallback((cambios: Partial<Persistida>) => {
    setValores((v) => {
      const nuevo = { ...v, ...cambios };
      AsyncStorage.setItem(CLAVE, JSON.stringify(nuevo)).catch(() => {});
      return nuevo;
    });
  }, []);

  const registrarMeta = useCallback((meta: Meta, pedido: string) => {
    setHistorial((h) => [{ meta, pedido, hora: new Date() }, ...h].slice(0, 20));
  }, []);

  const ctx = useMemo(
    () => ({ ...valores, cambiar, historial, registrarMeta }),
    [valores, cambiar, historial, registrarMeta],
  );

  if (!cargado) return null;
  return <Contexto.Provider value={ctx}>{children}</Contexto.Provider>;
}

export function useConfig(): ConfigCtx {
  const ctx = useContext(Contexto);
  if (!ctx) throw new Error('useConfig fuera de ConfigProvider');
  return ctx;
}
