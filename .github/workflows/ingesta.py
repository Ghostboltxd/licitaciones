import os
import json
import datetime
import sys
import httpx

TICKET = os.environ["MP_TICKET"].strip()
BASE = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"


def main():
    hoy = datetime.date.today().strftime("%d%m%Y")
    params = {"fecha": hoy, "ticket": TICKET}

    print("== DIAGNOSTICO ==")
    print("Ticket: largo", len(TICKET), "| empieza con", TICKET[:4], "| termina con", TICKET[-4:])
    print("fecha enviada:", hoy)

    respuesta = httpx.get(BASE, params=params, timeout=60)
    crudo = respuesta.text

    print("HTTP status:", respuesta.status_code)
    print("Respuesta cruda (600 caracteres):")
    print(crudo[:600])
    print("=================")

    os.makedirs("datos", exist_ok=True)
    with open("datos/respuesta_cruda.txt", "w", encoding="utf-8") as f:
        f.write("HTTP " + str(respuesta.status_code) + "\n")
        f.write("fecha=" + hoy + "\n")
        f.write("ticket_largo=" + str(len(TICKET)) + "\n")
        f.write("ticket_empieza=" + TICKET[:4] + "\n\n")
        f.write(crudo)

    if respuesta.status_code != 200:
        print("ERROR: la API respondio con status", respuesta.status_code)
        sys.exit(1)

    datos = respuesta.json()

    if "Listado" not in datos:
        print("ERROR: la respuesta no trae 'Listado'.")
        sys.exit(1)

    licitaciones = datos.get("Listado") or []
    print(f"Licitaciones encontradas: {len(licitaciones)}")

    with open(f"datos/{hoy}.json", "w", encoding="utf-8") as archivo:
        json.dump(licitaciones, archivo, ensure_ascii=False, indent=2)

    print(f"Guardado en datos/{hoy}.json")


if __name__ == "__main__":
    main()
