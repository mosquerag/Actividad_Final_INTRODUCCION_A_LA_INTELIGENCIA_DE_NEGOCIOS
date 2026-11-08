# Observatorio de Permanencia · Actividad 2

**Curso:** Introducción a la Inteligencia de Negocios
**Entrega:** A2_Grupo# (reemplazar # por el número del grupo)
**Integrantes:** Nombre 1 · Nombre 2 · Nombre 3 · Nombre 4
**Página pública:** https://mosquerag.github.io/Actividad_Final_INTRODUCCION_A_LA_INTELIGENCIA_DE_NEGOCIOS/
**Repositorio:** [https://github.com/mosquerag/Actividad_Final_INTRODUCCION_A_LA_INTELIGENCIA_DE_NEGOCIOS](https://github.com/mosquerag/Actividad_Final_INTRODUCCION_A_LA_INTELIGENCIA_DE_NEGOCIOS)

Observatorio web de permanencia estudiantil para la cohorte 2025-1 de la Universidad Andina del Norte (institución y datos sintéticos). Integra cinco fuentes mediante un ETL reproducible, un modelo dimensional, una arquitectura BI objetivo, un tablero interactivo con filtros y una regla de alerta temprana mejorada.

---

## Contenido del repositorio

| Ruta | Descripción |
|---|---|
| `index.html` | Página web con los seis retos y el tablero interactivo |
| `assets/styles.css` | Estilos de la página |
| `assets/data.js` | Datos agregados que alimentan el tablero (generado por el ETL) |
| `assets/app.js` | Filtros, indicadores, semáforos y gráfico |
| `assets/modelo_powerbi.png` | Captura de la vista de modelo (Reto 2) |
| `etl_observatorio.py` | ETL en Python (Reto 1) |
| `resultados/cohorte_limpia_publica.csv` | Cohorte limpia y anonimizada (1.200 estudiantes) |
| `resultados/registro_transformaciones.csv` | Registro de reglas del ETL |
| `A2_Grupo#_observatorio.pbix` | Modelo estrella en Power BI Desktop |
| `README.md` | Este archivo |

Los cinco CSV originales contienen nombres, documentos y correos, por lo que no se publican. El ETL se ejecuta sobre la carpeta de fuentes entregada por el curso.

---

## Cómo reejecutar el ETL

Requisitos: Python 3.9 o superior y pandas.

```bash
pip install pandas
python etl_observatorio.py fuentes_originales resultados
```

`fuentes_originales/` debe contener:

- `admisiones.csv`
- `sis_matriculas.csv`
- `erp_pagos_2025_2.csv`
- `moodle_actividad_2025_1.csv`
- `bienestar_registros_2025_1.csv`

El script también acepta los nombres con doble extensión (`.csv.csv`).

**Salidas** (carpeta `resultados/`): `cohorte_limpia.csv` (uso interno, con datos personales), `cohorte_limpia_publica.csv` (anónima), `admisiones_unicas.csv`, `sis_2025_2_limpio.csv`, `erp_limpio.csv`, `moodle_largo.csv`, `bienestar_anonimizado.csv`, `registro_transformaciones.csv`, `promedios_fuera_de_escala.csv` (uso interno) y `data.js`.

Para actualizar el tablero, copiar `resultados/data.js` a `assets/data.js`.

---

## Resultados de referencia

Al ejecutar el ETL sobre los datos originales debe obtenerse:

| Indicador | Valor |
|---|---|
| Estudiantes de la cohorte | 1.200 |
| Admitidos únicos | 1.450 |
| Absorción | 82,76 % |
| Matriculados en 2025-2 | 1.025 |
| Retención | 85,42 % |
| Desertores / deserción | 175 / 14,58 % |
| Promedio de la cohorte | 3,38 (n = 1.162 con promedio válido) |
| Regla actual | 371 alertados · precisión 32,61 % · cobertura 69,14 % |
| Regla nueva | 117 alertados · precisión 56,41 % · cobertura 37,71 % |

### Definiciones usadas

- **Absorción:** estudiantes de la cohorte ÷ admitidos únicos.
- **Retención:** estudiantes de la cohorte matriculados en 2025-2 ÷ estudiantes de la cohorte. **Deserción** = 100 % − retención.
- **Regla actual:** promedio de las notas parciales de las semanas 4 y 8 menor a 3,0 (escala 0–5) o 0 accesos sumando las semanas 7 y 8.
- **Precisión:** alertados que desertaron ÷ alertados. **Cobertura:** alertados que desertaron ÷ total de desertores.

### Regla de alerta nueva (Reto 5)

Se alerta si se cumplen al menos 3 de 4 señales en las semanas 1 a 8 de Moodle:

1. Accesos totales S1–S8 ≤ 22.
2. Accesos S6–S8 ≤ 6.
3. Promedio de notas S4 y S8 menor a 50/100.
4. Cuatro o más semanas con máximo 2 accesos.

Resultado: 117 alertados (capacidad ≤ 120) y cobertura de 37,71 % (mínimo 35 %).

---

## Decisiones de calidad de datos

- **Llave de integración:** código institucional. Moodle se asocia por código validado contra SIS, no por correo.
- **Homónimos en Bienestar:** el cruce se hace por nombre + programa y el ETL falla si esa llave es ambigua.
- **Promedios fuera de escala:** 13 registros tienen valores entre 24 y 43 (fuera de 0–5). Se excluyen del promedio sin convertirlos y se listan aparte. Otros 25 registros no tienen promedio.
- **Registro de transformaciones:** 14 reglas documentadas (problema, regla y etapa).

---

## Privacidad

- La descarga pública no contiene nombre, documento, correo ni observaciones de Bienestar.
- El código de estudiante se reemplaza por un identificador anónimo (hash).
- En la arquitectura objetivo, Bienestar se anonimiza antes de entrar a la zona bronce del lake.

---

## Modelo dimensional

- **Granularidad:** una fila por estudiante de la cohorte 2025-1 con su seguimiento en 2025-2.
- **Hechos:** `Hechos_Cohorte`. Medidas aditivas: matriculado, desertor, alertas, accesos. No aditivas: promedios, notas, retención, deserción, absorción, precisión y cobertura.
- **Dimensiones:** `Dim_Programa` (programa y facultad), `Dim_Estrato`, `Dim_TipoColegio` y `Dim_EstadoPago`.
- Las relaciones son uno a varios y permiten filtrar por programa, facultad y estrato.

---

## Tablero

Filtros combinables por programa, facultad y estrato. Muestra absorción, retención, deserción por programa, promedio de la cohorte, alertados, precisión y cobertura (regla actual y regla nueva), con semáforo frente a metas propuestas por el equipo:

| Indicador | Meta |
|---|---|
| Absorción | ≥ 80 % |
| Retención | ≥ 88 % |
| Deserción | ≤ 12 % |
| Promedio | ≥ 3,5 |
| Alertados | ≤ 120 (solo aplica a la cohorte completa) |
| Precisión | ≥ 40 % |
| Cobertura | ≥ 35 % |

Las razones se recalculan como cociente de sumas, no como promedio de porcentajes.

---

## Limitaciones

- Los datos son sintéticos y la regla nueva se calibró sobre esta misma cohorte. Debe validarse con otra cohorte antes de usarse en producción.
- El tablero publicado usa estadísticas agregadas; la descarga anónima incluye filas individuales sin datos identificables.

---

## Referencias

Ver la sección **Referencias** de la página 

Elmasri, R. y Navathe, S. B. (2015). Fundamentals of Database Systems [Fundamentos de los sistemas de bases de datos]. Pearson

- Sadalage, P. y Fowler, M. (2012). NoSQL distilled: A brief guide to the emerging world of polyglot persistence [NoSQL en esencia: Una breve guía al emergente mundo de la persistencia políglota]. Addison-Wesley.


- Kimball, R., y Caserta, J. (2004). The Data Warehouse ETL Toolkit: Practical Techniques for Extracting, Cleaning, Conforming, and Delivering Data [El kit de herramientas ETL para almacenes de datos: Técnicas prácticas para extraer, limpiar, conformar y entregar datos]. Wiley. www.nibmehub.com(se abre en una nueva pestaña)

-
- Kimball, R., y Ross, M. (2013). The Data Warehouse Toolkit: The Complete Guide to Dimensional Modeling [El kit de herramientas del almacén de datos: La guía completa para el modelado dimensional]. Wiley. www.ia801609.us.archive.org(se abre en una nueva pestaña)

-
Marston, S., Li, Z., Bandyopadhyay, S., Zhang, J. y Ghalsasi, A. (2011). Cloud computing—The business perspective [Computación en la nube: la perspectiva empresarial]. Decision Support Systems, 51(1), 176–189. www.doi.org(se abre en una nueva pestaña)

-
-Robinson, I., Webber, J. y Eifrem, E. (2015). Graph Databases: New Opportunities for Connected Data [Bases de datos de grafos: Nuevas oportunidades para datos conectados]. O'Reilly Media. www.web4.ensiie.fr(se abre en una nueva pestaña)

-
Zikopoulos, P., Eaton, C., deRoos, D., y Deutsch, T. (2012). Understanding Big Data: Analytics for Enterprise Class Hadoop and Streaming Data [Comprender el Big Data: Analítica para Hadoop y datos en streaming de clase empresarial]. McGraw-Hill. www.personal.utdallas.edu
