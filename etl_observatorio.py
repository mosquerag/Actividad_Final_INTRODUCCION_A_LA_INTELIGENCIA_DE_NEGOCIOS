
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ETL - OBSERVATORIO DE PERMANENCIA
Actividad 2 - Introducción a la Inteligencia de Negocios

Uso:
    python etl_observatorio.py carpeta_fuentes carpeta_salida

Archivos de entrada esperados:
    admisiones.csv
    sis_matriculas.csv
    erp_pagos_2025_2.csv
    moodle_actividad_2025_1.csv
    bienestar_registros_2025_1.csv

Salidas:
    cohorte_limpia.csv
    admisiones_unicas.csv
    sis_2025_2_limpio.csv
    erp_limpio.csv
    moodle_largo.csv
    bienestar_anonimizado.csv
    registro_transformaciones.csv

Nota:
El script requiere las cinco fuentes originales. No reconstruye
información faltante a partir de la cohorte ya consolidada.
"""

import sys
from pathlib import Path
import pandas as pd


# ============================================================
# 1. CATÁLOGOS DE NORMALIZACIÓN
# ============================================================

PROGRAMAS = {
    "Administración de Empresas":
        ("Adm.", "Ciencias Económicas y Administrativas"),

    "Contaduría Pública":
        ("Cont.", "Ciencias Económicas y Administrativas"),

    "Ingeniería Industrial":
        ("Ing. Ind.", "Ingeniería"),

    "Ingeniería Informática":
        ("Ing. Inf.", "Ingeniería"),

    "Psicología":
        ("Psico.", "Ciencias Sociales y Humanas"),

    "Trabajo Social":
        ("T. Social", "Ciencias Sociales y Humanas"),
}

VARIANTES_SIS = {
    "ADMON EMPRESAS": "Administración de Empresas",
    "PSICOLOGIA": "Psicología",
    "ING. INFORMATICA": "Ingeniería Informática",
    "CONTADURIA": "Contaduría Pública",
    "ING INDUSTRIAL": "Ingeniería Industrial",
    "TRABAJO SOCIAL": "Trabajo Social",
}

ABREV_BIENESTAR = {
    abreviatura: programa
    for programa, (abreviatura, facultad) in PROGRAMAS.items()
}

MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4,
    "may": 5, "jun": 6, "jul": 7, "ago": 8,
    "sep": 9, "oct": 10, "nov": 11, "dic": 12
}


# ============================================================
# 2. FUNCIONES AUXILIARES
# ============================================================

def leer_csv(carpeta, nombre):
    """Lee un archivo CSV como texto para controlar conversiones."""
    # ruta = Path(carpeta) / nombre
    ruta = Path(carpeta) / nombre

    if not ruta.exists():  
        ruta = Path(carpeta) / (nombre + ".csv")
        
    # if not ruta.exists():
    #     raise FileNotFoundError(
    #         f"No se encontró el archivo requerido: {ruta}"
    #     )

    return pd.read_csv(
        ruta,
        dtype=str,
        encoding="utf-8-sig"
    )


def registrar(log, fuente, problema, regla, etapa, filas):
    """Registra cada regla aplicada durante el ETL."""
    log.append({
        "fuente": fuente,
        "problema": problema,
        "regla": regla,
        "etapa": etapa,
        "filas_afectadas": int(filas)
    })


def parse_fecha(valor):
    """Convierte fechas en formatos habituales a fecha estándar."""

    if pd.isna(valor):
        return pd.NaT

    valor = str(valor).strip()

    if not valor:
        return pd.NaT

    # Formato dd/mm/aaaa
    if "/" in valor:
        dia, mes, anio = valor.split("/")
        return pd.Timestamp(
            int(anio), int(mes), int(dia)
        )

    # Formato aaaa-mm-dd
    if len(valor) >= 10 and valor[4] == "-":
        return pd.Timestamp(valor)

    # Formato dd-mmm-aaaa
    partes = valor.split("-")

    if len(partes) == 3:
        dia, mes_texto, anio = partes

        mes = MESES[mes_texto.lower()[:3]]

        return pd.Timestamp(
            int(anio), mes, int(dia)
        )

    raise ValueError(f"Formato de fecha no reconocido: {valor}")


def normalizar_documento(serie):
    """Elimina separadores de miles y espacios."""
    return (
        serie.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", "", regex=False)
    )


def validar_columnas(df, columnas, fuente):
    """Verifica que existan las columnas requeridas."""
    faltantes = set(columnas) - set(df.columns)

    if faltantes:
        raise ValueError(
            f"Faltan columnas en {fuente}: {sorted(faltantes)}"
        )


# ============================================================
# 3. PROCESO PRINCIPAL
# ============================================================

def ejecutar_etl(carpeta_entrada, carpeta_salida):

    entrada = Path(carpeta_entrada)
    salida = Path(carpeta_salida)

    salida.mkdir(parents=True, exist_ok=True)

    log = []

    # --------------------------------------------------------
    # 3.1. EXTRACCIÓN DE LAS CINCO FUENTES
    # --------------------------------------------------------

    adm = leer_csv(entrada, "admisiones.csv")
    sis = leer_csv(entrada, "sis_matriculas.csv")
    erp = leer_csv(entrada, "erp_pagos_2025_2.csv")
    moodle = leer_csv(entrada, "moodle_actividad_2025_1.csv")
    bienestar = leer_csv(entrada, "bienestar_registros_2025_1.csv")

    validar_columnas(
        adm,
        [
            "documento", "nombre_completo", "programa",
            "fecha_admision", "puntaje_saber11",
            "estrato", "tipo_colegio"
        ],
        "admisiones.csv"
    )

    validar_columnas(
        sis,
        [
            "documento", "programa", "periodo",
            "tipo_ingreso", "creditos", "promedio_periodo"
        ],
        "sis_matriculas.csv"
    )

    validar_columnas(
        erp,
        [
            "documento", "estado_pago", "valor_liquidado"
        ],
        "erp_pagos_2025_2.csv"
    )

    validar_columnas(
        moodle,
        [
            "correo", "semana", "accesos",
            "nota_parcial_0_100"
        ],
        "moodle_actividad_2025_1.csv"
    )

    validar_columnas(
        bienestar,
        [
            "programa", "nombre_completo",
            "tipo_registro", "fecha", "observacion"
        ],
        "bienestar_registros_2025_1.csv"
    )

    # --------------------------------------------------------
    # 3.2. LIMPIEZA DE ADMISIONES
    # --------------------------------------------------------

    filas_iniciales = len(adm)

    adm["nombre"] = (
        adm["nombre_completo"]
        .str.strip()
        .str.title()
    )

    registrar(
        log,
        "admisiones",
        "Nombres con mayúsculas y formatos inconsistentes",
        "Normalizar nombres con strip() y title()",
        "Limpieza",
        filas_iniciales
    )

    adm["fecha_admision"] = adm["fecha_admision"].map(parse_fecha)

    registrar(
        log,
        "admisiones",
        "Fechas en diferentes formatos",
        "Convertir fechas a formato estándar",
        "Transformación",
        filas_iniciales
    )

    adm["documento"] = normalizar_documento(adm["documento"])

    adm["documento"] = pd.to_numeric(
        adm["documento"],
        errors="raise"
    ).astype("int64")

    adm = adm.drop_duplicates(
        subset=["documento"],
        keep="first"
    ).copy()

    adm["programa"] = adm["programa"].str.strip().replace(VARIANTES_SIS)
    desconocidos = set(adm["programa"]) - set(PROGRAMAS)
    if desconocidos:
        raise ValueError(
            f"Programas desconocidos en admisiones: {desconocidos}"
        )

    

    registrar(
        log,
        "admisiones",
        "Registros repetidos por documento",
        "Conservar un registro por documento único",
        "Limpieza",
        filas_iniciales - len(adm)
    )

    adm["estrato"] = pd.to_numeric(
        adm["estrato"],
        errors="coerce"
    )

    adm["puntaje_saber11"] = pd.to_numeric(
        adm["puntaje_saber11"],
        errors="coerce"
    )

    adm = adm[
        [
            "documento", "nombre", "programa",
            "fecha_admision", "puntaje_saber11",
            "estrato", "tipo_colegio"
        ]
    ]

    # --------------------------------------------------------
    # 3.3. LIMPIEZA DEL SISTEMA DE INFORMACIÓN ACADÉMICA
    # --------------------------------------------------------

    sis["documento"] = normalizar_documento(sis["documento"])

    sis["documento"] = pd.to_numeric(
        sis["documento"],
        errors="raise"
    ).astype("int64")

    sis["programa"] = sis["programa"].str.strip()

    sis["programa"] = sis["programa"].replace(VARIANTES_SIS)

    registrar(
        log,
        "sis_matriculas",
        "Nombres de programas con abreviaturas y variantes",
        "Aplicar catálogo de equivalencias de programas",
        "Transformación",
        len(sis)
    )

    sis["periodo"] = sis["periodo"].str.strip().replace({
        "2025-II": "2025-2",
        "2025-I": "2025-1"
    })

    registrar(
        log,
        "sis_matriculas",
        "Periodos con numeración romana",
        "Estandarizar periodo a AAAA-N",
        "Limpieza",
        len(sis)
    )

    sis["promedio_periodo"] = pd.to_numeric(
        sis["promedio_periodo"]
        .str.replace(",", ".", regex=False),
        errors="coerce"
    )

    sis["creditos"] = pd.to_numeric(
        sis["creditos"],
        errors="coerce"
    )

    duplicados_sis = sis.duplicated().sum()

    sis = sis.drop_duplicates().copy()

    registrar(
        log,
        "sis_matriculas",
        "Filas duplicadas",
        "Eliminar duplicados exactos",
        "Limpieza",
        duplicados_sis
    )

    # Cohorte de estudiantes nuevos del periodo 2025-1.
    cohorte = sis[
        (sis["periodo"] == "2025-1") &
        (sis["tipo_ingreso"].str.strip().str.lower() == "nuevo")
    ].copy()

    registrar(
        log,
        "sis_matriculas",
        "Identificación de estudiantes pertenecientes a la cohorte",
        "Seleccionar periodo 2025-1 y tipo de ingreso Nuevo",
        "Transformación",
        len(cohorte)
    )

    sis_2025_2 = sis[
        sis["periodo"] == "2025-2"
    ].copy()

    sis_2025_2 = sis_2025_2.drop_duplicates(
        subset=["documento"],
        keep="last"
    )

    # --------------------------------------------------------
    # 3.4. LIMPIEZA DEL ERP DE PAGOS
    # --------------------------------------------------------

    erp["documento"] = normalizar_documento(erp["documento"])

    erp["documento"] = pd.to_numeric(
        erp["documento"],
        errors="raise"
    ).astype("int64")

    erp["estado_pago"] = (
        erp["estado_pago"]
        .str.strip()
        .str.lower()
        .str.capitalize()
    )

    erp["valor_liquidado"] = pd.to_numeric(
        erp["valor_liquidado"],
        errors="coerce"
    )

    registrar(
        log,
        "erp_pagos_2025_2",
        "Documentos y estados de pago con formatos inconsistentes",
        "Normalizar documentos, estados y valores monetarios",
        "Limpieza",
        len(erp)
    )

    # --------------------------------------------------------
    # 3.5. LIMPIEZA E INTEGRACIÓN DE MOODLE
    # --------------------------------------------------------

    moodle["semana"] = pd.to_numeric(
        moodle["semana"],
        errors="raise"
    ).astype(int)

    moodle["accesos"] = pd.to_numeric(
        moodle["accesos"],
        errors="coerce"
    ).fillna(0).astype(int)

    moodle["nota_parcial_0_100"] = pd.to_numeric(
        moodle["nota_parcial_0_100"],
        errors="coerce"
    )

    registrar(
        log,
        "moodle_actividad",
        "Accesos y calificaciones almacenados como texto",
        "Convertir accesos y notas a tipos numéricos",
        "Limpieza",
        len(moodle)
    )

    # El correo no debe asumirse como llave única.
    # Se verifica primero si está duplicado en la cohorte.
    adm_cohorte = cohorte.merge(
        adm[["documento", "nombre"]],
        on="documento",
        how="left"
    )

    if "codigo" not in adm_cohorte.columns:
        raise ValueError(
            "No existe la columna codigo en la fuente SIS. "
            "Se necesita una llave sustituta para integrar Moodle."
        )

    adm_cohorte["numero_codigo"] = (
        adm_cohorte["codigo"]
        .astype(str)
        .str[-4:]
        .astype(int)
    )

    # Esta asociación por bloques solo es válida si la estructura
    # original de Moodle está documentada y se verifica contra SIS.
    if len(moodle) % 16 != 0:
        raise ValueError(
            "El archivo Moodle no contiene bloques completos de 16 semanas."
        )

    moodle = moodle.reset_index(drop=True)

    moodle["bloque"] = (
        moodle.index // 16
    ) + 1

    verificacion = (
        moodle.groupby("bloque")["correo"]
        .first()
        .reset_index()
        .merge(
            adm_cohorte[
                ["numero_codigo", "correo_institucional"]
            ],
            left_on="bloque",
            right_on="numero_codigo",
            how="left"
        )
    )

    if verificacion["correo_institucional"].isna().any():
        raise ValueError(
            "No fue posible validar todos los bloques Moodle contra SIS."
        )

    coincidencias = (
        verificacion["correo"].str.strip().str.lower() ==
        verificacion["correo_institucional"].str.strip().str.lower()
    )

    if not coincidencias.all():
        raise ValueError(
            "La asociación de Moodle por bloques no coincide con SIS. "
            "Se requiere una llave de integración confiable."
        )

    mapa_codigo = adm_cohorte[
        ["numero_codigo", "codigo"]
    ].drop_duplicates()

    moodle = moodle.merge(
        mapa_codigo,
        left_on="bloque",
        right_on="numero_codigo",
        how="left"
    )

    if moodle["codigo"].isna().any():
        raise ValueError(
            "Existen registros Moodle sin código de estudiante."
        )

    moodle_largo = moodle[
        [
            "codigo", "semana", "accesos",
            "nota_parcial_0_100"
        ]
    ].copy()

    registrar(
        log,
        "moodle_actividad",
        "Correo compartido o no confiable como llave única",
        "Validar la relación con el código institucional del estudiante",
        "Integración",
        len(moodle_largo)
    )

    # --------------------------------------------------------
    # 3.6. LIMPIEZA DE BIENESTAR
    # --------------------------------------------------------

    bienestar["programa"] = (
        bienestar["programa"]
        .str.strip()
        .map(ABREV_BIENESTAR)
    )

    if bienestar["programa"].isna().any():
        raise ValueError(
            "Hay abreviaturas de programa en Bienestar sin equivalencia."
        )

    bienestar["nombre"] = (
        bienestar["nombre_completo"]
        .str.strip()
        .str.title()
    )

    bienestar["fecha"] = bienestar["fecha"].map(parse_fecha)
    
    n_hom = int((adm.groupby("nombre")["documento"].nunique() > 1).sum())
    registrar(log, "bienestar_registros",
                "Homónimos: mismo nombre en estudiantes distintos",
                "Cruzar por nombre + programa y validar que sea único",
                "Integración", n_hom)

    cohorte_nombres = cohorte.merge(
        adm[["documento", "nombre"]],
        on="documento",
        how="left"
    )

    # Se verifica que nombre + programa identifique un único estudiante.
    conteos = (
        cohorte_nombres
        .groupby(["nombre", "programa"])["documento"]
        .nunique()
    )

    claves_ambiguas = conteos[conteos > 1]

    if not claves_ambiguas.empty:
        raise ValueError(
            "Existen homónimos con el mismo nombre y programa en Bienestar. "
            "Se necesita una llave adicional para resolverlos sin ambigüedad."
        )

    bienestar_integrado = bienestar.merge(
        cohorte_nombres[
            ["nombre", "programa", "documento"]
        ],
        on=["nombre", "programa"],
        how="left",
        validate="many_to_one"
    )

    if bienestar_integrado["documento"].isna().any():
        raise ValueError(
            "Hay registros de Bienestar que no se pudieron asociar "
            "con un estudiante de la cohorte."
        )

    # Se eliminan nombre y observación por privacidad.
    bienestar_anonimizado = bienestar_integrado[
        ["documento", "tipo_registro", "fecha"]
    ].copy()

    registrar(
        log,
        "bienestar_registros",
        "Nombre y observación pueden contener datos personales o sensibles",
        "Eliminar nombre y observación; conservar llave y tipo de registro",
        "Anonimización",
        len(bienestar_anonimizado)
    )

    # --------------------------------------------------------
    # 3.7. INTEGRACIÓN DE LA COHORTE
    # --------------------------------------------------------

    coh = cohorte.merge(
        adm,
        on="documento",
        how="left",
        suffixes=("", "_adm"),
        validate="one_to_one"
    )

    if coh["nombre"].isna().any():
        raise ValueError(
            "Hay estudiantes de la cohorte sin correspondencia en admisiones."
        )

    coh["matriculado_2025_2"] = (
        coh["documento"].isin(sis_2025_2["documento"])
    ).astype(int)

    coh["desertor"] = 1 - coh["matriculado_2025_2"]

    erp_unico = erp.drop_duplicates(
        subset=["documento"],
        keep="last"
    )

    coh = coh.merge(
        erp_unico[["documento", "estado_pago"]],
        on="documento",
        how="left",
        validate="one_to_one"
    )

    coh["estado_pago_2025_2"] = (
        coh["estado_pago"].fillna("Sin liquidación")
    )

    coh["facultad"] = coh["programa"].map(
        lambda programa: PROGRAMAS.get(
            programa,
            (None, "Sin clasificar")
        )[1]
    )

    # --------------------------------------------------------
    # 3.8. VARIABLES DE MOODLE
    # --------------------------------------------------------

    accesos = moodle_largo.pivot_table(
        index="codigo",
        columns="semana",
        values="accesos",
        aggfunc="sum"
    )

    for semana in range(1, 9):
        if semana not in accesos.columns:
            accesos[semana] = 0

    accesos = accesos[
        list(range(1, 9))
    ].fillna(0)

    accesos.columns = [
        f"acc_s{semana}"
        for semana in accesos.columns
    ]

    coh = coh.merge(
        accesos.reset_index(),
        on="codigo",
        how="left",
        validate="one_to_one"
    )

    columnas_accesos = [
        f"acc_s{semana}"
        for semana in range(1, 9)
    ]

    coh[columnas_accesos] = (
        coh[columnas_accesos].fillna(0)
    )

    notas = moodle_largo[
        moodle_largo["semana"].isin([4, 8])
    ].pivot_table(
        index="codigo",
        columns="semana",
        values="nota_parcial_0_100",
        aggfunc="mean"
    )

    notas = notas.rename(columns={
        4: "nota_s4",
        8: "nota_s8"
    })

    coh = coh.merge(
        notas.reset_index(),
        on="codigo",
        how="left",
        validate="one_to_one"
    )

    coh["prom_nota_s4_s8_0a5"] = (
        coh[["nota_s4", "nota_s8"]]
        .mean(axis=1)
        / 20
    )

    coh["acc_s7_s8"] = (
        coh["acc_s7"] + coh["acc_s8"]
    )

    # Regla actual de alerta.
    coh["alerta_actual"] = (
        (coh["prom_nota_s4_s8_0a5"] < 3.0) |
        (coh["acc_s7_s8"] == 0)
    ).astype(int)

    # Regla propuesta:
    # Al menos 3 de 4 señales de riesgo.
    total_accesos = coh[columnas_accesos].sum(axis=1)

    semanas_baja_actividad = (
        coh[columnas_accesos] <= 2
    ).sum(axis=1)

    senal_1 = total_accesos <= 22
    # senal_2 = coh["acc_s7"] + coh["acc_s8"] <= 6
    senal_2 = (
        coh["acc_s6"] +
        coh["acc_s7"] +
        coh["acc_s8"]
    ) <= 6
    senal_3 = coh["prom_nota_s4_s8_0a5"] < 2.5
    senal_4 = semanas_baja_actividad >= 4

    coh["puntaje_riesgo"] = (
        senal_1.astype(int) +
        senal_2.astype(int) +
        senal_3.astype(int) +
        senal_4.astype(int)
    )

    coh["alerta_nueva"] = (
        coh["puntaje_riesgo"] >= 3
    ).astype(int)

    registrar(
        log,
        "Moodle + SIS",
        "Indicadores tempranos de riesgo académico",
        "Calcular regla de alerta con cuatro señales y umbral de tres",
        "Transformación",
        len(coh)
    )

    # --------------------------------------------------------
    # 3.9. VALIDACIONES DE CALIDAD
    # --------------------------------------------------------

    if len(coh) != 1200:
        raise ValueError(
            f"Se esperaban 1.200 estudiantes; se encontraron {len(coh)}."
        )

    if not coh["documento"].is_unique:
        raise ValueError(
            "La cohorte contiene documentos duplicados."
        )

    if not (coh["matriculado_2025_2"] + coh["desertor"]).eq(1).all():
        raise ValueError(
            "La clasificación de matrícula y deserción no suma uno."
        )

    # if (coh["promedio_2025_1"] > 5).any():
    #     print(
    #         "ADVERTENCIA: hay promedios académicos superiores a 5. "
    #         "Revisar escala y fuente; no se modifican automáticamente."
    #     )    
    # if (coh["promedio_periodo"] > 5).any():
    #         print(
    #             "ADVERTENCIA: hay promedios académicos superiores a 5. "
    #             "Revisar escala y fuente; no se modifican automáticamente."
    #         )

    fuera = (coh["promedio_periodo"] > 5) | (coh["promedio_periodo"] < 0)
    prom_crudo = coh["promedio_periodo"].mean()
    coh[fuera][["codigo", "promedio_periodo"]].to_csv(
        salida / "promedios_fuera_de_escala.csv", index=False
    )
    coh["promedio_periodo"] = coh["promedio_periodo"].where(~fuera)
    print(f"Promedios fuera de 0-5: {int(fuera.sum())} | sin promedio: "
          f"{int(coh['promedio_periodo'].isna().sum()) - int(fuera.sum())}")
    print(f"Promedio con valores anómalos: {prom_crudo:.4f} | "
          f"excluyéndolos: {coh['promedio_periodo'].mean():.4f}")
    registrar(log, "sis_matriculas", "Promedios fuera de la escala 0-5",
              "Marcar como no válidos y excluir del promedio (sin convertir)",
              "Validación", int(fuera.sum()))

    if (coh["prom_nota_s4_s8_0a5"] > 5).any():
        print(
            "ADVERTENCIA: hay notas derivadas superiores a 5."
        )

    # --------------------------------------------------------
    # 3.10. PREPARAR SALIDA LIMPIA
    # --------------------------------------------------------

    # columnas_salida = [
    #     "codigo",
    #     "documento",
    #     "nombre",
    #     "programa",
    #     "facultad",
    #     "estrato",
    #     "tipo_colegio",
    #     "puntaje_saber11",
    #     "creditos",
    #     "promedio_periodo",
    #     "matriculado_2025_2",
    #     "desertor",
    #     "estado_pago_2025_2",
    #     "nota_s4",
    #     "nota_s8",
    #     "prom_nota_s4_s8_0a5",
    #     "acc_s7_s8",
    #     "alerta_actual",
    #     "alerta_nueva",
    #     "puntaje_riesgo"
    # ] + columnas_accesos


    # Se renombran variables para facilitar su lectura.
    coh = coh.rename(columns={
        "promedio_periodo": "promedio_2025_1"
    })

    columnas_salida = [
        "codigo", "documento", "nombre", "programa",
        "facultad", "estrato", "tipo_colegio",
        "puntaje_saber11", "creditos",
        "promedio_2025_1", "matriculado_2025_2",
        "desertor", "estado_pago_2025_2",
        "nota_s4", "nota_s8",
        "prom_nota_s4_s8_0a5", "acc_s7_s8",
        "alerta_actual", "alerta_nueva",
        "puntaje_riesgo"
    ] + columnas_accesos

    coh = coh[columnas_salida].copy()

    coh = coh.sort_values(
        "codigo"
    ).reset_index(drop=True)
    import hashlib

    pub = coh.drop(columns=["documento", "nombre"]).copy()
    pub["codigo"] = pub["codigo"].astype(str).map(
        lambda c: hashlib.sha256(("obs-" + c).encode()).hexdigest()[:10]
    )
    pub = pub.rename(columns={"codigo": "id_anonimo"})
    pub.to_csv(
        salida / "cohorte_limpia_publica.csv",
        index=False,
        encoding="utf-8-sig"
    )

    exportar_data_js(coh, adm, salida)


    # --------------------------------------------------------
    # 3.11. EXPORTACIÓN DE RESULTADOS
    # --------------------------------------------------------

    coh.to_csv(
        salida / "cohorte_limpia.csv",
        index=False,
        encoding="utf-8-sig"
    )

    adm.to_csv(
        salida / "admisiones_unicas.csv",
        index=False,
        encoding="utf-8-sig"
    )

    sis_2025_2.to_csv(
        salida / "sis_2025_2_limpio.csv",
        index=False,
        encoding="utf-8-sig"
    )

    erp.to_csv(
        salida / "erp_limpio.csv",
        index=False,
        encoding="utf-8-sig"
    )

    moodle_largo.to_csv(
        salida / "moodle_largo.csv",
        index=False,
        encoding="utf-8-sig"
    )

    bienestar_anonimizado.to_csv(
        salida / "bienestar_anonimizado.csv",
        index=False,
        encoding="utf-8-sig"
    )

    pd.DataFrame(log).to_csv(
        salida / "registro_transformaciones.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # 3.12. RESUMEN DE EJECUCIÓN
    # --------------------------------------------------------

    total = len(coh)
    matriculados = int(coh["matriculado_2025_2"].sum())
    desertores = int(coh["desertor"].sum())

    print("\nETL FINALIZADO")
    print("------------------------------")
    print("Estudiantes:", total)
    print("Matriculados:", matriculados)
    print("Desertores:", desertores)
    print(
        "Retención: {:.2f}%".format(
            matriculados / total * 100
        )
    )
    print(
        "Deserción: {:.2f}%".format(
            desertores / total * 100
        )
    )
    print(
        "Alertas actuales:",
        int(coh["alerta_actual"].sum())
    )
    print(
        "Alertas nuevas:",
        int(coh["alerta_nueva"].sum())
    )
    tp_a = int((coh["alerta_actual"] * coh["desertor"]).sum())
    tp_n = int((coh["alerta_nueva"] * coh["desertor"]).sum())
    print(f"Absorción: {total / len(adm) * 100:.2f}%  ({total}/{len(adm)})")
    print(f"Regla actual: precisión {tp_a / coh['alerta_actual'].sum() * 100:.2f}% | "
          f"cobertura {tp_a / desertores * 100:.2f}%")
    print(f"Regla nueva:  precisión {tp_n / coh['alerta_nueva'].sum() * 100:.2f}% | "
          f"cobertura {tp_n / desertores * 100:.2f}%")
    print(
        "Reglas documentadas:",
        len(log)
    )
    print("Carpeta de salida:", salida.resolve())

    return coh


# ============================================================
# 4. EJECUCIÓN DESDE TERMINAL
# ============================================================

import json

METAS = {"absorcion": 80, "retencion": 88, "desercion": 12, "promedio": 3.5,
         "alertados": 120, "precision": 40, "cobertura": 35}

def exportar_data_js(coh, adm, salida):
    est = lambda e: "Sin dato" if pd.isna(e) else str(int(e))
    coh = coh.copy(); adm = adm.copy()
    coh["grp"] = coh["estrato"].map(est)
    adm["grp"] = adm["estrato"].map(est)
    adm["facultad"] = adm["programa"].map(lambda p: PROGRAMAS[p][1])
    claves = ["programa", "facultad", "grp"]
    coh["tp_actual"] = coh["alerta_actual"] * coh["desertor"]
    coh["tp_nueva"] = coh["alerta_nueva"] * coh["desertor"]
    g = coh.groupby(claves).agg(
        cohorte=("codigo", "size"), matriculados=("matriculado_2025_2", "sum"),
        desertores=("desertor", "sum"), promedio=("promedio_2025_1", "mean"),
        nPromedio=("promedio_2025_1", "count"),
        alertasActuales=("alerta_actual", "sum"), tpActual=("tp_actual", "sum"),
        alertasNuevas=("alerta_nueva", "sum"), tpNueva=("tp_nueva", "sum"),
    ).reset_index()
    # g = g.merge(adm.groupby(claves).size().rename("admitidos").reset_index(),
    #             on=claves, how="left")
    # g["admitidos"] = g["admitidos"].fillna(0).astype(int)
        adm_g = adm.groupby(claves).size().rename("admitidos").reset_index()
    g = g.merge(adm_g, on=claves, how="outer")
    cols_num = ["cohorte", "matriculados", "desertores", "nPromedio",
                "alertasActuales", "tpActual", "alertasNuevas", "tpNueva", "admitidos"]
    g[cols_num] = g[cols_num].fillna(0).astype(int)
    assert g["admitidos"].sum() == len(adm), "admitidos no suman el total"
    g["promedio"] = g["promedio"].round(4).where(g["promedio"].notna(), None)
    g = g.rename(columns={"grp": "estrato"})
    assert g["cohorte"].sum() == 1200
    assert (g["admitidos"] >= g["cohorte"]).all(), "admitidos < cohorte en algún grupo"
    data = {
        "metadata": {"nombre": "Observatorio de Permanencia", "cohorte": "2025-1",
                     "periodoSeguimiento": "2025-2", "totalEstudiantes": int(g["cohorte"].sum()),
                     "totalAdmitidos": int(len(adm)),
                     "naturalezaDatos": "Datos académicos sintéticos para ejercicio académico"},
        "metas": METAS,
        "registros": json.loads(g.to_json(orient="records")),
    }
    (salida / "data.js").write_text(
        "const OBSERVATORIO_DATA = " + json.dumps(data, ensure_ascii=False, indent=2)
        + ";\nwindow.OBSERVATORIO_DATA = OBSERVATORIO_DATA;\n", encoding="utf-8")

if __name__ == "__main__":

    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    ejecutar_etl(
        sys.argv[1],
        sys.argv[2]
    )
