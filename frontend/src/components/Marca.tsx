import { Text, View } from 'react-native';

import { colores, fuentes } from './ui';

/** Marca del header: sello "BA" + "Pasaporte BA" en serif con BA en coral. */
export function Marca() {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, marginLeft: 16 }}>
      <View style={{
        width: 36, height: 40, borderRadius: 7, borderBottomLeftRadius: 12, borderBottomRightRadius: 12,
        backgroundColor: colores.primario, alignItems: 'center', justifyContent: 'center',
      }}>
        <Text style={{ color: colores.blanco, fontFamily: fuentes.titulo, fontSize: 16, transform: [{ rotate: '-4deg' }] }}>BA</Text>
      </View>
      <View>
        <Text style={{ fontFamily: fuentes.extra, fontSize: 9, letterSpacing: 1.6, color: colores.suave }}>TU CIUDAD,</Text>
        <Text style={{ fontFamily: fuentes.titulo, fontSize: 23, color: colores.texto, marginTop: -2 }}>
          Pasaporte <Text style={{ fontFamily: fuentes.tituloItalica, color: colores.acento }}>BA</Text>
        </Text>
      </View>
    </View>
  );
}
