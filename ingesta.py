import os
import json
import datetime
import time
import smtplib
import httpx
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

TICKET = os.environ["MP_TICKET"].strip()
BASE = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"

# ================= CONFIGURACION =================
# Edita esto sin tocar el resto del codigo.

REGIONES = []   # vacio = TODAS las regiones de Chile.
                # Ej: ["Metropolitana"] para solo Santiago.

NICHOS = {
    "impresion": {
        "palabras": [
            "impresi", "imprenta", "fotocopi", "anillad", "encuadern",
            "gigantograf", "plotter", "ploteo", "señaletic", "senaletic",
            "letrero", "afiche", "follet", "volante", "talonario",
            "formulario", "credencial", "sticker", "adhesiv", "etiquet",
            "serigraf", "sublima", "grafic", "gráfic", "publicaci",
            "catalogo", "catálogo", "pendon", "pendón", "troquelad",
            "laminad", "plastificad", "editorial", "difusion",
        ],
        "categorias": ["8212", "82101500"],
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


def pedir(params, intentos=3, espera=5):
    for i in range(1, intentos + 1):
        try:
            r = httpx.get(BASE, params=params, timeout=60)
            print("  intento", i, ": HTTP", r.status_code)
            if r.status_code == 200:
                return r.json()
            if i == intentos:
                print("  respuesta:", r.text[:300])
        except Exception as e:
            print("  intento", i, ": error ->", e)
        time.sleep(espera)
    return None


def bajar_listado(hoy):
    print("Bajando listado por fecha", hoy)
    datos = pedir({"fecha": hoy, "ticket": TICKET})
    if datos and datos.get("Listado"):
        return datos["Listado"]
    print("Respaldo: probando estado=activas")
    datos = pedir({"estado": "activas", "ticket": TICKET})
    if datos and datos.get("Listado"):
        return datos["Listado"]
    print("ERROR: no se pudo bajar el listado.")
    return []


def bajar_detalle(codigo):
    datos = pedir({"codigo": codigo, "ticket": TICKET}, intentos=2, espera=2)
    if not datos:
        return None
    lista = datos.get("Listado") or []
    return lista[0] if lista else None


def esta_abierta(cierre_str):
    if not cierre_str:
        return False
    try:
        cierre = datetime.datetime.fromisoformat(cierre_str)
    except ValueError:
        return False
    ahora = datetime.datetime.now(ZoneInfo("America/Santiago")).replace(tzinfo=None)
    return cierre > ahora


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


def fmt_monto(m):
    if m is None:
        return "No publicado"
    return "$" + f"{int(m):,}".replace(",", ".")


def fmt_cierre(s):
    if not s:
        return "-"
    try:
        return datetime.datetime.fromisoformat(s).strftime("%d-%m %H:%M")
    except ValueError:
        return s


def construir_html(regs, hoy):
    if not regs:
        return (f"<div style='font-family:Arial'><h2>Licitaciones de impresion</h2>"
                f"<p>Hoy ({hoy}) no hay licitaciones de impresion abiertas.</p></div>")
    filas = ""
    for r in regs:
        enlace = ("https://www.mercadopublico.cl/Procurement/Modules/RFB/"
                  "DetailsAcquisition.aspx?idlicitacion=" + str(r["codigo"]))
        filas += (
            "<tr>"
            f"<td style='padding:10px;border-bottom:1px solid #eee'>"
            f"<b>{r['nombre']}</b><br>"
            f"<span style='color:#666;font-size:13px'>{r['organismo']} - {r['region']}</span>"
            "</td>"
            f"<td style='padding:10px;border-bottom:1px solid #eee;white-space:nowrap'>"
            f"<b>{fmt_monto(r['monto'])}</b></td>"
            f"<td style='padding:10px;border-bottom:1px solid #eee;white-space:nowrap'>"
            f"{fmt_cierre(r['cierre'])}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #eee'>"
            f"<a href='{enlace}'>Ver ficha</a></td>"
            "</tr>"
        )
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:800px">
      <h2 style="color:#0a3d62;margin-bottom:4px">Licitaciones de impresion abiertas</h2>
      <p style="color:#666;margin-top:0">Fecha: {hoy} &nbsp;|&nbsp; Total: {len(regs)}</p>
      <table style="border-collapse:collapse;width:100%">
        <tr style="background:#f4f4f4;text-align:left">
          <th style="padding:10px">Licitacion</th>
          <th style="padding:10px">Monto</th>
          <th style="padding:10px">Cierra</th>
          <th style="padding:10px"></th>
        </tr>
        {filas}
      </table>
      <p style="color:#999;font-size:12px">Fuente: Direccion ChileCompra - API Mercado Publico</p>
    </div>
    """


def enviar_correo(asunto, html):
    usuario = os.environ.get("MAIL_USER")
    clave = os.environ.get("MAIL_PASS")
    destino = os.environ.get("MAIL_TO")
    if not (usuario and clave and destino):
        print("Sin configuracion de correo. No se envia.")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = usuario
    msg["To"] = destino
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(usuario, clave)
        s.sendmail(usuario, [destino], msg.as_string())
    print("Correo enviado a", destino)


def main():
    hoy = datetime.datetime.now(ZoneInfo("America/Santiago")).strftime("%d%m%Y")
    print("Fecha (hora Chile):", hoy)

    listado = bajar_listado(hoy)
    print("Total licitaciones del dia:", len(listado))
    if not listado:
        print("Sin datos. Se detiene.")
        return

    todas = []
    for cfg in NICHOS.values():
        todas += cfg["palabras"]

    candidatas = [l for l in listado if coincide_palabra(l.get("Nombre"), todas)]
    print("Candidatas por palabra clave:", len(candidatas))
    print("-" * 50)

    resultados = {n: [] for n in NICHOS}

    for i, lic in enumerate(candidatas, 1):
        codigo = lic.get("CodigoExterno")
        det = bajar_detalle(codigo)
        if not det:
            continue

        nichos = clasificar(det)
        if not nichos:
            continue

        comprador = det.get("Comprador") or {}
        fechas = det.get("Fechas") or {}
        items = (det.get("Items") or {}).get("Listado") or []
        cierre = fechas.get("FechaCierre")

        if not esta_abierta(cierre):
            print(f"[{i}/{len(candidatas)}] {codigo} -> ya cerro, se omite")
            continue

        registro = {
            "codigo": codigo,
            "nombre": det.get("Nombre"),
            "organismo": comprador.get("NombreOrganismo"),
            "region": (comprador.get("RegionUnidad") or "").strip(),
            "comuna": comprador.get("ComunaUnidad"),
            "monto": det.get("MontoEstimado"),
            "moneda": det.get("Moneda"),
            "cierre": cierre,
            "categorias": sorted({str(x.get("CodigoCategoria")) for x in items}),
        }

        for n in nichos:
            resultados[n].append(registro)

        print(f"[{i}/{len(candidatas)}] {codigo} -> {', '.join(nichos)}")
        time.sleep(0.3)

    os.makedirs("datos", exist_ok=True)
    print("-" * 50)
    for nicho, regs in resultados.items():
        regs.sort(key=lambda r: (r["cierre"] or ""))
        archivo = f"datos/{hoy}_{nicho}.json"
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(regs, f, ensure_ascii=False, indent=2)
        print(f"{nicho}: {len(regs)} licitaciones -> {archivo}")

    regs = resultados["impresion"]
    html = construir_html(regs, hoy)
    enviar_correo(f"Licitaciones de impresion - {hoy} ({len(regs)})", html)


if __name__ == "__main__":
    main()
