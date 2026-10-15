"""Ejecuta las mismas operaciones contra MySQL y HBase y compara resultados y tiempos.

Requiere el backend corriendo y los mismos datos cargados en ambos motores (dev/seed_dev.py).
Uso (desde backend/):  .venv/Scripts/python -m dev.comparar_motores
"""

import json
import sys
import urllib.error
import urllib.request

API = "http://localhost:8000"


def llamar(motor: str, metodo: str, ruta: str, cuerpo: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(
        API + ruta, method=metodo, headers={"X-Motor": motor, "Content-Type": "application/json"},
        data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def comparar(nombre: str, ruta: str, normalizar=lambda d: d):
    resultados = {m: llamar(m, "GET", ruta) for m in ("mysql", "hbase")}
    (s1, r1), (s2, r2) = resultados["mysql"], resultados["hbase"]
    d1, d2 = normalizar(r1.get("data")), normalizar(r2.get("data"))
    igual = s1 == s2 and d1 == d2
    t1 = r1.get("meta", {}) or {}
    t2 = r2.get("meta", {}) or {}
    print(f"{'OK ' if igual else 'DIF'} {nombre:<38} mysql {t1.get('duracion_ms', '-'):>7} ms "
          f"({len(t1.get('operaciones', []))} ops) | hbase {t2.get('duracion_ms', '-'):>7} ms "
          f"({len(t2.get('operaciones', []))} ops)")
    if not igual:
        print("   mysql:", s1, json.dumps(d1, ensure_ascii=False)[:300])
        print("   hbase:", s2, json.dumps(d2, ensure_ascii=False)[:300])
    return igual


sin_cursor = lambda d: {**d, "siguiente_cursor": None} if isinstance(d, dict) else d


def probar_crud(motor: str) -> bool:
    """Ciclo completo de alta, modificación y baja en un motor."""
    pasos = []
    s, r = llamar(motor, "POST", "/lugares", {"nombre": "Café de Prueba", "direccion": "Defensa 100",
                                              "latitud": -34.61, "longitud": -58.37, "id_categoria": 2, "id_barrio": 4})
    pasos.append(("crear lugar", s == 201))
    id_l = r["data"]["id"]
    s, r = llamar(motor, "PUT", f"/lugares/{id_l}", {"nombre": "Café Renombrado", "direccion": None,
                                                     "latitud": None, "longitud": None, "id_categoria": 1, "id_barrio": 5})
    pasos.append(("modificar lugar", s == 200 and r["data"]["nombre"] == "Café Renombrado"
                  and r["data"]["barrio"]["id"] == 5 and r["data"]["latitud"] is None))
    s, r = llamar(motor, "GET", "/lugares?barrio=5&q=renombrado")
    pasos.append(("aparece en índice nuevo", s == 200 and any(x["id"] == id_l for x in r["data"]["items"])))
    s, r = llamar(motor, "GET", "/lugares?barrio=4&q=prueba")
    pasos.append(("no queda en índice viejo", s == 200 and not any(x["id"] == id_l for x in r["data"]["items"])))
    s, r = llamar(motor, "POST", "/checkins", {"id_usuario": 1, "id_lugar": id_l, "puntaje": 5, "comentario": "Prueba"})
    pasos.append(("crear check-in", s == 201))
    id_c = r["data"]["id"]
    s, r = llamar(motor, "PUT", f"/checkins/{id_c}", {"puntaje": 3, "comentario": None})
    pasos.append(("modificar check-in", s == 200 and r["data"]["puntaje"] == 3 and r["data"]["comentario"] is None))
    s, r = llamar(motor, "GET", f"/lugares/{id_l}/checkins")
    pasos.append(("check-in visible en el lugar", s == 200 and r["data"]["items"][0]["id"] == id_c))
    s, _ = llamar(motor, "DELETE", f"/lugares/{id_l}")
    pasos.append(("borrar lugar con check-ins -> 409", s == 409))
    s, _ = llamar(motor, "DELETE", f"/checkins/{id_c}")
    pasos.append(("borrar check-in", s == 200))
    s, _ = llamar(motor, "DELETE", f"/lugares/{id_l}")
    pasos.append(("borrar lugar", s == 200))
    s, _ = llamar(motor, "GET", f"/lugares/{id_l}")
    pasos.append(("lugar borrado -> 404", s == 404))
    s, _ = llamar(motor, "POST", "/checkins", {"id_usuario": 1, "id_lugar": 999999})
    pasos.append(("check-in a lugar inexistente -> 422", s == 422))
    s, _ = llamar(motor, "POST", "/usuarios", {"nombre_usuario": "ana.garcia", "nombre": "x", "email": "x@x.com"})
    pasos.append(("usuario duplicado -> 409", s in (409, 201)))  # 201 si ana.garcia no existe en el seed
    ok = all(p for _, p in pasos)
    for nombre, paso in pasos:
        if not paso:
            print(f"   FALLÓ [{motor}] {nombre}")
    print(f"{'OK ' if ok else 'DIF'} CRUD completo en {motor}")
    return ok


if __name__ == "__main__":
    pruebas = [
        comparar("barrios", "/barrios"),
        comparar("categorías", "/categorias"),
        comparar("lugares (página 1)", "/lugares?limite=10", sin_cursor),
        comparar("lugares por barrio", "/lugares?barrio=14&limite=50", sin_cursor),
        comparar("lugares por categoría", "/lugares?categoria=1&limite=50", sin_cursor),
        comparar("lugares por barrio + categoría", "/lugares?barrio=14&categoria=1&limite=50", sin_cursor),
        comparar("lugares por texto", "/lugares?q=farol&limite=50", sin_cursor),
        comparar("detalle de lugar", "/lugares/17"),
        comparar("lugares cercanos (1 km)", "/lugares/cercanos?lat=-34.58&lon=-58.425&radio_m=1000"),
        comparar("check-ins de un lugar", "/lugares/17/checkins?limite=10", sin_cursor),
        comparar("check-ins de un usuario", "/usuarios/3/checkins?limite=10", sin_cursor),
        comparar("usuario", "/usuarios/3"),
        comparar("ranking por barrio (mes)", "/consultas/ranking-barrio?barrio=14&mes=2026-08&top=10"),
        comparar("pasaporte", "/consultas/pasaporte/3"),
        comparar("lugar inexistente (404)", "/lugares/999999"),
        probar_crud("mysql"),
        probar_crud("hbase"),
    ]
    print(f"\n{sum(pruebas)}/{len(pruebas)} pruebas OK")
    sys.exit(0 if all(pruebas) else 1)
