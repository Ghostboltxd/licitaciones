import os
import json
import datetime
import sys
import httpx

TICKET = os.environ["MP_TICKET"].strip()
BASE = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"


def bajar_licitaciones(hoy):
    params = {"fecha": hoy, "ticket": TICKET}
    print("== DIAGNOSTICO ==")
    print("Ticket: largo", len(TICKET), "| empieza con", TICKET[:4], "| termina con", TICKET[-4:])
    print("Parametros enviados: fecha =", hoy, "| ticket = ***")
    respuesta = httpx.get(BASE, params=params, timeout=60)
    print("HTTP status:", respuesta.status_code)
    print("Respuesta cruda (primeros 600 caracteres):")
    print(respuesta.text[:600])
    print("=================")
    respuesta.raise_for_status()
    return respuesta.json()


def main():
    hoy = datetime.date.today().strftime("%d%m%Y")
    datos = bajar_licitaciones(hoy)

    if "Listado" not in datos:
        print("ERROR: la respuesta no trae 'Listado'. La API devolvio un error.")
        sys.exit(1)

    licitaciones = datos.get("Listado") or []

    print(f"Fecha: {hoy}")
    print(f"Licitaciones encontradas: {len(licitaciones)}")
    print("-" * 50)

    for lic in licitaciones[:5]:
        nombre = lic.get("Nombre", "sin nombre")
        cierre = lic.get("FechaCierre", "sin fecha")
        print(f"- {nombre[:70]}")
        print(f"  cierra: {cierre}")

    os.makedirs("datos", exist_ok=True)
    with open(f"datos/{hoy}.json", "w", encoding="utf-8") as archivo:
        json.dump(licitaciones, archivo, ensure_ascii=False, indent=2)

    print("-" * 50)
    print(f"Guardado en datos/{hoy}.json")


if __name__ == "__main__":
    main()
