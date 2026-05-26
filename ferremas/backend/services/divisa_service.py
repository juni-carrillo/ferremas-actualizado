import httpx
from datetime import datetime
from typing import Optional


# Banco Central de Chile API – series de tipo de cambio
# Documentación: https://si3.bcentral.cl/estadisticas/Principal1/Metodologias/API/api.html
BCENTRAL_BASE = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"

# Códigos de series del Banco Central
SERIES = {
    "USD": "F073.TCO.PRE.Z.D",   # Dólar observado
    "EUR": "F072.CLP.EUR.N.O.D", # Euro
    "GBP": "F072.CLP.GBP.N.O.D", # Libra esterlina
}

# Credenciales de ejemplo (reemplazar con las reales del Banco Central)
# Se obtienen registrándose en: https://si3.bcentral.cl/estadisticas/
BCENTRAL_USER = "tu_email@ejemplo.com"
BCENTRAL_PASS = "tu_password_bcentral"


async def obtener_tipo_cambio(moneda: str) -> Optional[float]:
    """
    Consulta el tipo de cambio de la moneda indicada (USD, EUR, GBP) desde la API
    del Banco Central de Chile. Retorna el valor en CLP por unidad de moneda extranjera.
    """
    serie = SERIES.get(moneda.upper())
    if not serie:
        return None

    hoy = datetime.now().strftime("%Y-%m-%d")

    params = {
        "user": BCENTRAL_USER,
        "pass": BCENTRAL_PASS,
        "function": "GetSeries",
        "timeseries": serie,
        "firstdate": hoy,
        "lastdate": hoy,
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(BCENTRAL_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
            # La respuesta tiene la estructura: {"Series": {"Obs": [{"value": "..."}]}}
            observaciones = data.get("Series", {}).get("Obs", [])
            if observaciones:
                return float(observaciones[-1]["value"])
    except Exception as e:
        print(f"[BancoCentral] Error al consultar tipo de cambio: {e}")

    # Fallback con valores aproximados cuando la API no está disponible
    fallback = {"USD": 950.0, "EUR": 1030.0, "GBP": 1200.0}
    return fallback.get(moneda.upper())


async def convertir_a_clp(monto: float, moneda_origen: str) -> dict:
    """Convierte un monto en moneda extranjera a CLP."""
    if moneda_origen.upper() == "CLP":
        return {
            "moneda_origen": "CLP",
            "moneda_destino": "CLP",
            "valor_unitario": 1.0,
            "monto_original": monto,
            "monto_convertido": monto,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
        }

    tipo_cambio = await obtener_tipo_cambio(moneda_origen)
    if not tipo_cambio:
        raise ValueError(f"Moneda no soportada: {moneda_origen}")

    return {
        "moneda_origen": moneda_origen.upper(),
        "moneda_destino": "CLP",
        "valor_unitario": tipo_cambio,
        "monto_original": monto,
        "monto_convertido": round(monto * tipo_cambio, 2),
        "fecha": datetime.now().strftime("%Y-%m-%d"),
    }
