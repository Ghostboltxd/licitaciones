import os
import json
import datetime
import time
import httpx

TICKET = os.environ["MP_TICKET"].strip()
BASE = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"

# ================= CONFIGURACION =================
# Edita esto sin tocar el resto del codigo.

REGIONES = []   # vacio = TODAS las regiones.
                # Ej: ["Metropolitana", "Valparaíso", "Biobío"]

NICHOS = {
    "impresion": {
        "palabras": [
            "impresi", "imprenta", "fotocopi", "anillad", "encuadern",
            "gigantograf", "plotter", "ploteo", "señaletic", "senaletic",
            "letrero", "afiche", "follet", "volante", "talonario",
            "formulario", "credencial", "toner", "tóner", "cartucho",
            "sticker", "adhesiv", "etiquet", "serigraf", "sublima",
            "grafic", "gráfic", "publicaci", "catalogo", "catálogo",
            "pendon", "pendón", "troquelad", "laminad", "plastificad",
        ],
        "categorias": ["8212", "82101500", "5510", "141115", "441031", "4510"],
    },
    "aseo_insumos": {
        "palabras": [
            "articulos de aseo", "artículos de aseo", "insumos de aseo",
            "materiales de aseo", "elementos de aseo", "insumos de limpieza",
            "articulos de limpieza", "artículos de limpieza",
            "desinfect", "jabon", "jabón", "cloro", "detergente",
            "papel higienic", "toalla de papel", "bolsa de basura",
            "bolsas de basura", "guantes de latex", "guantes de látex",
        ],
        "categorias": ["47", "141117"],
    },
}
# =================================================


def coincide_palabra(nombre, palabras):
    n = (nombre or "").lower()
    return any(p in n for p in palabras)


def region_ok(region):
    if not REGIONES:
        return True
    r = (region or "").lower()
    return any(x.lower() in r for x in REGIONES)


def bajar_listado(hoy):
    r = httpx.get(BASE, params={"fecha": hoy, "ticket": TICKET}, timeout=60)
    r.raise_for_status()
    return r.json().get("Listado") or []


def bajar_detalle(codigo):
    r = httpx.get(BASE, params={"codigo": codigo, "ticket": TICKET}, timeout=60)
    r.raise_for_status()
    lista = r.json().get("Listado") or []
    return lista[0] if lista else None


def clasificar(det):
    comprador = det.get("Comprador") or {}
    if not region_ok(comprador.get("RegionUnidad", "")):
        return []
    items = (det.get("Items") or {}).get("Listado") or []
    cats = [str(i.get("CodigoCategoria", "")) for i in items]
    encontrados = []
    for nicho, cfg in NICHOS.items():
        if any(c.startswith(p) for c in cats for p in cfg["categorias"]):
            encontrados.append(nicho)
    return encontrados


def main():
    hoy = datetime.date.today().strftime("%d%m%Y")
    print("Fecha:", hoy)

    listado = bajar_listado(hoy)
    print("Total licitaciones del dia:", len(listado))

    todas = []
    for cfg in NICHOS.values():
        todas += cfg["palabras"]

    candidatas = [l for l in listado if coincide_palabra(l.get("Nombre"), todas)]
    print("Candidatas por palabra clave:", len(candidatas))
    print("-" * 50)

    resultados = {n: [] for n in NICHOS}

    for i, lic in enumerate(candidatas, 1):
        codigo = lic.get("CodigoExterno")
        try:
            det = bajar_detalle(codigo)
        except Exception as e:
            print("Error con", codigo, ":", e)
            continue
        if not det:
            continue

        nichos = clasificar(det)
        if not nichos:
            continue

        comprador = det.get("Comprador") or {}
        fechas = det.get("Fechas") or {}
        items = (det.get("Items") or {}).get("Listado") or []

        registro = {
            "codigo": codigo,
            "nombre": det.get("Nombre"),
            "organismo": comprador.get("NombreOrganismo"),
            "region": (comprador.get("RegionUnidad") or "").strip(),
            "comuna": comprador.get("ComunaUnidad"),
            "monto": det.get("MontoEstimado"),
            "moneda": det.get("Moneda"),
            "cierre": fechas.get("FechaCierre"),
            "categorias": sorted({str(x.get("CodigoCategoria")) for x in items}),
        }

        for n in nichos:
            resultados[n].append(registro)

        print(f"[{i}/{len(candidatas)}] {codigo} -> {', '.join(nichos)}")
        time.sleep(0.3)

    os.makedirs("datos", exist_ok=True)
    print("-" * 50)
    for nicho, regs in resultados.items():
        archivo = f"datos/{hoy}_{nicho}.json"
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(regs, f, ensure_ascii=False, indent=2)
        print(f"{nicho}: {len(regs)} licitaciones -> {archivo}")


if __name__ == "__main__":
    main()
