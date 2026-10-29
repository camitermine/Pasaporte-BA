// Configuracion persistida: conexion, sesion autenticada y modo de diagnostico.

import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Platform } from 'react-native';

import type { Meta, Sesion, Usuario } from './tipos';

const CLAVE = 'pasaporteba:config:v2';

export interface Registro {
  meta: Meta;
  pedido: string;
  hora: Date;
}

interface Persistida {
  apiUrl: string;
  token: string | null;
  usuario: Usuario | null;
  debug: boolean;
}

interface ConfigCtx extends Persistida {
  cargado: boolean;
  cambiar: (cambios: Partial<Pick<Persistida, 'apiUrl' | 'debug'>>) => void;
  establecerSesion: (sesion: Sesion) => void;
  limpiarSesion: () => void;
  historial: Registro[];
  registrarMeta: (meta: Meta, pedido: string) => void;
}

function urlPorDefecto(): string {
  if (Platform.OS === 'web') return 'http://localhost:8000';
  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  return host ? `http://${host}:8000` : 'http://192.168.0.17:8000';
}

const Contexto = createContext<ConfigCtx | null>(null);

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [cargado, setCargado] = useState(false);
  const [valores, setValores] = useState<Persistida>({
    apiUrl: urlPorDefecto(), token: null, usuario: null, debug: true,
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

  const guardar = useCallback((nuevo: Persistida) => {
    AsyncStorage.setItem(CLAVE, JSON.stringify(nuevo)).catch(() => {});
    return nuevo;
  }, []);

  const cambiar = useCallback((cambios: Partial<Pick<Persistida, 'apiUrl' | 'debug'>>) => {
    setValores((v) => guardar({ ...v, ...cambios }));
  }, [guardar]);

  const establecerSesion = useCallback((sesion: Sesion) => {
    setValores((v) => guardar({ ...v, token: sesion.token, usuario: sesion.usuario }));
  }, [guardar]);

  const limpiarSesion = useCallback(() => {
    setValores((v) => guardar({ ...v, token: null, usuario: null }));
  }, [guardar]);

  const registrarMeta = useCallback((meta: Meta, pedido: string) => {
    setHistorial((h) => [{ meta, pedido, hora: new Date() }, ...h].slice(0, 20));
  }, []);

  const ctx = useMemo(
    () => ({ ...valores, cargado, cambiar, establecerSesion, limpiarSesion, historial, registrarMeta }),
    [valores, cargado, cambiar, establecerSesion, limpiarSesion, historial, registrarMeta],
  );

  if (!cargado) return null;
  return <Contexto.Provider value={ctx}>{children}</Contexto.Provider>;
}

export function useConfig(): ConfigCtx {
  const ctx = useContext(Contexto);
  if (!ctx) throw new Error('useConfig fuera de ConfigProvider');
  return ctx;
}
