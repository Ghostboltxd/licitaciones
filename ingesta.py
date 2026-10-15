import os
import json
import datetime
import httpx

TICKET = os.environ["MP_TICKET"]
BASE = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"


def bajar_licitaciones():
    respuesta = httpx.get(
        BASE,
        params={"estado": "activas", "ticket": TICKET},
        timeout=60,
    )
    respuesta.raise_for_status()
    return respuesta.json()


def main():
    hoy = datetime.date.today().strftime("%d%m%Y")
    datos = bajar_licitaciones()
    licitaciones = datos.get("Listado") or []

    print(f"Fecha: {hoy}")
    print(f"Licitaciones activas encontradas: {len(licitaciones)}")
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
