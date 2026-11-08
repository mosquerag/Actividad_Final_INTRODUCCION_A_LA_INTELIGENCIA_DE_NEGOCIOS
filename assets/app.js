/* =====================================================
   OBSERVATORIO DE PERMANENCIA
   Archivo: assets/app.js

   Funciones:
   - Navegación entre secciones.
   - Filtros combinados.
   - Cálculo de indicadores.
   - Gráfico de deserción por programa.
   - Semáforos de metas.
   - Tabla de resultados agregados.
   ===================================================== */

"use strict";

// =====================================================
// 1. CONFIGURACIÓN Y DATOS
// =====================================================

const DATA = window.OBSERVATORIO_DATA;

if (!DATA || !Array.isArray(DATA.registros)) {
  console.error("No se encontró OBSERVATORIO_DATA. Revisa data.js.");
  throw new Error("No se pudieron cargar los datos del observatorio.");
}

const registros = DATA.registros;
const resumenGlobal = DATA.resumen;
const metas = DATA.metas;

// =====================================================
// 2. FUNCIONES AUXILIARES
// =====================================================

function elemento(id) {
  return document.getElementById(id);
}

function formatoNumero(valor, decimales = 0) {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) {
    return "N/D";
  }

  return new Intl.NumberFormat("es-CO", {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(valor);
}

function porcentaje(valor) {
  return valor === null || !Number.isFinite(valor)
    ? "N/D"
    : formatoNumero(valor, 2) + "%";
}

function tasa(numerador, denominador) {
  return denominador > 0 ? (numerador / denominador) * 100 : null;
}

function escaparHTML(texto) {
  return String(texto)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function suma(filas, campo) {
  return filas.reduce((total, fila) => total + (Number(fila[campo]) || 0), 0);
}

// function promedioPonderado(filas) {
//     const totalEstudiantes = suma(filas, "cohorte");

//     if (!totalEstudiantes) return null;

//     const sumaPonderada = filas.reduce(
//         (total, fila) =>
//             total + (Number(fila.promedio) || 0) * fila.cohorte,
//         0
//     );

//     return sumaPonderada / totalEstudiantes;
// }

function promedioPonderado(filas) {
  const n = suma(filas, "nPromedio");
  if (!n) return null;
  return (
    filas.reduce(
      (t, f) => t + (Number(f.promedio) || 0) * (f.nPromedio || 0),
      0,
    ) / n
  );
}

// =====================================================
// 3. NAVEGACIÓN ENTRE SECCIONES
// =====================================================

function iniciarNavegacion() {
  const enlaces = document.querySelectorAll(".sidebar nav a");
  const paginas = document.querySelectorAll("main .page");

  function mostrarPagina(id) {
    paginas.forEach((pagina) => {
      pagina.hidden = pagina.id !== id;
    });

    enlaces.forEach((enlace) => {
      const activo = enlace.getAttribute("href") === "#" + id;

      enlace.classList.toggle("active", activo);
    });

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });

    // Actualizar tablero cuando se abre.
    if (id === "tablero") {
      actualizarTablero();
    }
  }

  enlaces.forEach((enlace) => {
    enlace.addEventListener("click", (evento) => {
      evento.preventDefault();

      const id = enlace.getAttribute("href").substring(1);

      mostrarPagina(id);

      history.replaceState(null, "", "#" + id);
    });
  });

  // También funcionan los enlaces internos de las tarjetas.
  document.querySelectorAll('a[href^="#"]').forEach((enlace) => {
    if (enlace.closest(".sidebar nav")) return;

    enlace.addEventListener("click", (evento) => {
      const id = enlace.getAttribute("href").substring(1);
      const destino = elemento(id);

      if (destino && destino.classList.contains("page")) {
        evento.preventDefault();

        mostrarPagina(id);

        history.replaceState(null, "", "#" + id);
      }
    });
  });

  // Abrir la sección indicada en la URL.
  const paginaInicial = location.hash.replace("#", "");

  if (paginaInicial && elemento(paginaInicial)?.classList.contains("page")) {
    mostrarPagina(paginaInicial);
  } else {
    mostrarPagina("inicio");
  }
}

// =====================================================
// 4. TARJETAS DE INICIO
// =====================================================

function renderizarInicio() {
  const contenedor = elemento("homeMetrics");

  if (!contenedor) return;

  // const indicadores = [

  //     {
  //         nombre: "Estudiantes de la cohorte",
  //         valor: formatoNumero(resumenGlobal.cohorte),
  //         detalle: "Ingreso 2025-1"
  //     },

  //     {
  //         nombre: "Retención",
  //         valor: porcentaje(resumenGlobal.retencion),
  //         detalle: "Matrícula en 2025-2"
  //     },

  //     {
  //         nombre: "Deserción",
  //         valor: porcentaje(resumenGlobal.desercion),
  //         detalle: formatoNumero(resumenGlobal.desertores) + " estudiantes"
  //     },

  //     {
  //         nombre: "Promedio académico",
  //         valor: formatoNumero(resumenGlobal.promedioCohorte, 2),
  //         detalle: "Escala de 0 a 5"
  //     }

  // ];

  const g = calcularIndicadores(registros);
  const indicadores = [
    {
      nombre: "Estudiantes de la cohorte",
      valor: formatoNumero(g.cohorte),
      detalle: "Ingreso 2025-1",
    },
    {
      nombre: "Retención",
      valor: porcentaje(g.retencion),
      detalle: "Matrícula en 2025-2",
    },
    {
      nombre: "Deserción",
      valor: porcentaje(g.desercion),
      detalle: formatoNumero(g.desertores) + " estudiantes",
    },
    {
      nombre: "Promedio académico",
      valor: formatoNumero(g.promedio, 2),
      detalle: "Escala de 0 a 5 (sin valores anómalos)",
    },
  ];

  contenedor.innerHTML = indicadores
    .map(
      (indicador) => `

        <article class="metric">

            <span>${escaparHTML(indicador.nombre)}</span>

            <strong>${escaparHTML(indicador.valor)}</strong>

            <small>${escaparHTML(indicador.detalle)}</small>

        </article>

    `,
    )
    .join("");
}

// =====================================================
// 5. CARGAR OPCIONES DE LOS FILTROS
// =====================================================

function cargarFiltros() {
  const programa = elemento("programFilter");
  const facultad = elemento("facultyFilter");
  const estrato = elemento("stratumFilter");

  if (!programa || !facultad || !estrato) return;

  const programas = [...new Set(registros.map((fila) => fila.programa))].sort();

  const facultades = [
    ...new Set(registros.map((fila) => fila.facultad)),
  ].sort();

  const estratos = [...new Set(registros.map((fila) => fila.estrato))].sort(
    (a, b) => {
      return a.localeCompare(b, "es", { numeric: true });
    },
  );

  programa.innerHTML =
    '<option value="">Todos</option>' +
    programas
      .map(
        (valor) =>
          `<option value="${escaparHTML(valor)}">${escaparHTML(valor)}</option>`,
      )
      .join("");

  facultad.innerHTML =
    '<option value="">Todas</option>' +
    facultades
      .map(
        (valor) =>
          `<option value="${escaparHTML(valor)}">${escaparHTML(valor)}</option>`,
      )
      .join("");

  estrato.innerHTML =
    '<option value="">Todos</option>' +
    estratos
      .map(
        (valor) =>
          `<option value="${escaparHTML(valor)}">${escaparHTML(valor)}</option>`,
      )
      .join("");
}

// =====================================================
// 6. APLICAR FILTROS COMBINADOS
// =====================================================

function obtenerFilasFiltradas() {
  const programa = elemento("programFilter")?.value || "";
  const facultad = elemento("facultyFilter")?.value || "";
  const estrato = elemento("stratumFilter")?.value || "";

  return registros.filter((fila) => {
    const coincidePrograma = !programa || fila.programa === programa;

    const coincideFacultad = !facultad || fila.facultad === facultad;

    const coincideEstrato = !estrato || fila.estrato === estrato;

    return coincidePrograma && coincideFacultad && coincideEstrato;
  });
}

// =====================================================
// 7. CALCULAR INDICADORES DEL FILTRO
// =====================================================

function calcularIndicadores(filas) {
  const cohorte = suma(filas, "cohorte");
  const matriculados = suma(filas, "matriculados");
  const desertores = suma(filas, "desertores");

  const alertasActuales = suma(filas, "alertasActuales");
  const tpActual = suma(filas, "tpActual");

  const alertasNuevas = suma(filas, "alertasNuevas");
  const tpNueva = suma(filas, "tpNueva");

  const promedio = promedioPonderado(filas);

  return {
    cohorte,

    matriculados,

    desertores,

    retencion: tasa(matriculados, cohorte),

    desercion: tasa(desertores, cohorte),

    promedio,

    alertasActuales,

    precisionActual: tasa(tpActual, alertasActuales),

    coberturaActual: tasa(tpActual, desertores),

    alertasNuevas,

    precisionNueva: tasa(tpNueva, alertasNuevas),

    coberturaNueva: tasa(tpNueva, desertores),

    // absorcion: null
    admitidos: suma(filas, "admitidos"),
    absorcion: tasa(cohorte, suma(filas, "admitidos")),
  };
}

// =====================================================
// 8. TARJETAS DEL TABLERO
// =====================================================

function renderizarMetricas(indicadores) {
  const contenedor = elemento("dashboardMetrics");

  if (!contenedor) return;

  //   const tarjetas = [
  //     {
  //       nombre: "Absorción",
  //       valor: "Pendiente",
  //       detalle: "Falta total de admitidos únicos",
  //     },

  //     {
  //       nombre: "Retención",
  //       valor: porcentaje(indicadores.retencion),
  //       detalle:
  //         formatoNumero(indicadores.matriculados) + " estudiantes matriculados",
  //     },

  //     {
  //       nombre: "Deserción",
  //       valor: porcentaje(indicadores.desercion),
  //       detalle:
  //         formatoNumero(indicadores.desertores) + " estudiantes desertores",
  //     },

  //     {
  //       nombre: "Promedio cohorte",
  //       valor: formatoNumero(indicadores.promedio, 2),
  //       detalle: "Escala de 0 a 5",
  //     },

  //     {
  //       nombre: "Alertados · regla nueva",
  //       valor: formatoNumero(indicadores.alertasNuevas),
  //       detalle: "Capacidad máxima propuesta: 120",
  //     },

  //     {
  //       nombre: "Precisión · regla nueva",
  //       valor: porcentaje(indicadores.precisionNueva),
  //       detalle: "Verdaderos positivos / alertados",
  //     },

  //     {
  //       nombre: "Cobertura · regla nueva",
  //       valor: porcentaje(indicadores.coberturaNueva),
  //       detalle: "Verdaderos positivos / desertores",
  //     },
  //   ];

  const i = indicadores;
  const tarjetas = [
    {
      nombre: "Absorción",
      valor: porcentaje(i.absorcion),
      detalle:
        formatoNumero(i.cohorte) +
        " de " +
        formatoNumero(i.admitidos) +
        " admitidos únicos",
    },
    {
      nombre: "Retención",
      valor: porcentaje(i.retencion),
      detalle: formatoNumero(i.matriculados) + " matriculados en 2025-2",
    },
    {
      nombre: "Deserción",
      valor: porcentaje(i.desercion),
      detalle: formatoNumero(i.desertores) + " desertores",
    },
    {
      nombre: "Promedio cohorte",
      valor: formatoNumero(i.promedio, 2),
      detalle: "Escala de 0 a 5",
    },
    {
      nombre: "Alertados · regla actual",
      valor: formatoNumero(i.alertasActuales),
      detalle: "Notas S4-S8 < 3,0 o 0 accesos S7-S8",
    },
    {
      nombre: "Precisión · regla actual",
      valor: porcentaje(i.precisionActual),
      detalle: "Alertados que desertaron / alertados",
    },
    {
      nombre: "Cobertura · regla actual",
      valor: porcentaje(i.coberturaActual),
      detalle: "Alertados que desertaron / desertores",
    },
    {
      nombre: "Alertados · regla nueva",
      valor: formatoNumero(i.alertasNuevas),
      detalle: "Reto 5 · capacidad máxima: 120",
    },
    {
      nombre: "Precisión · regla nueva",
      valor: porcentaje(i.precisionNueva),
      detalle: "Reto 5",
    },
    {
      nombre: "Cobertura · regla nueva",
      valor: porcentaje(i.coberturaNueva),
      detalle: "Reto 5 · mínimo 35 %",
    },
  ];

  contenedor.innerHTML = tarjetas
    .map(
      (tarjeta) => `

        <article class="metric">

            <span>${escaparHTML(tarjeta.nombre)}</span>

            <strong>${escaparHTML(tarjeta.valor)}</strong>

            <small>${escaparHTML(tarjeta.detalle)}</small>

        </article>

    `,
    )
    .join("");
}

// =====================================================
// 9. GRÁFICO DE DESERCIÓN POR PROGRAMA
// =====================================================

function renderizarGrafico(filas) {
  const contenedor = elemento("dropoutChart");

  if (!contenedor) return;

  const grupos = {};

  filas.forEach((fila) => {
    if (!grupos[fila.programa]) {
      grupos[fila.programa] = {
        programa: fila.programa,
        cohorte: 0,
        desertores: 0,
      };
    }

    grupos[fila.programa].cohorte += fila.cohorte;
    grupos[fila.programa].desertores += fila.desertores;
  });

  //   const resultados = Object.values(grupos)
  //     .map((grupo) => ({
  //       ...grupo,
  //       tasa: tasa(grupo.desertores, grupo.cohorte),
  //     }))
  //     .sort((a, b) => b.tasa - a.tasa);

  const resultados = Object.values(grupos)
    .map((grupo) => ({
      ...grupo,
      tasa: tasa(grupo.desertores, grupo.cohorte),
    }))
    .filter((grupo) => grupo.tasa !== null)
    .sort((a, b) => b.tasa - a.tasa);

  if (!resultados.length) {
    contenedor.innerHTML =
      '<p class="muted">No hay datos para los filtros seleccionados.</p>';

    return;
  }

  contenedor.innerHTML = resultados
    .map((grupo) => {
      const ancho = Math.max(0, Math.min(100, grupo.tasa));

      return `

            <div class="bar-item">

                <span class="bar-label"
                      title="${escaparHTML(grupo.programa)}">
                    ${escaparHTML(grupo.programa)}
                </span>

                <div class="bar-track"
                     role="progressbar"
                     aria-valuenow="${grupo.tasa.toFixed(2)}"
                     aria-valuemin="0"
                     aria-valuemax="100"
                     aria-label="Deserción de ${escaparHTML(grupo.programa)}">

                    <div class="bar-fill"
                         style="width: ${ancho}%">
                    </div>

                </div>

                <span class="bar-value">
                    ${porcentaje(grupo.tasa)}
                </span>

            </div>

        `;
    })
    .join("");
}

// =====================================================
// 10. SEMÁFOROS
// =====================================================

function estadoMeta(valor, meta, tipo = "mayor") {
  if (valor === null || !Number.isFinite(valor)) {
    return {
      clase: "yellow",
      texto: "Sin dato",
    };
  }

  const cumple = tipo === "menor" ? valor <= meta : valor >= meta;

  return cumple
    ? {
        clase: "green",
        texto: "Cumple",
      }
    : {
        clase: "red",
        texto: "No cumple",
      };
}

// function renderizarSemaforos(indicadores) {
//   const contenedor = elemento("trafficLights");

//   if (!contenedor) return;

//   const indicadoresMeta = [
//     {
//       nombre: "Retención",
//       valor: indicadores.retencion,
//       meta: metas.retencion,
//       tipo: "mayor",
//       mostrar: porcentaje,
//     },

//     {
//       nombre: "Deserción",
//       valor: indicadores.desercion,
//       meta: metas.desercion,
//       tipo: "menor",
//       mostrar: porcentaje,
//     },

//     {
//       nombre: "Promedio académico",
//       valor: indicadores.promedio,
//       meta: metas.promedio,
//       tipo: "mayor",
//       mostrar: (valor) => formatoNumero(valor, 2),
//     },

//     {
//       nombre: "Alertados · regla nueva",
//       valor: indicadores.alertasNuevas,
//       meta: metas.alertados,
//       tipo: "menor",
//       mostrar: (valor) => formatoNumero(valor),
//     },

//     {
//       nombre: "Precisión · regla nueva",
//       valor: indicadores.precisionNueva,
//       meta: metas.precision,
//       tipo: "mayor",
//       mostrar: porcentaje,
//     },

//     {
//       nombre: "Cobertura · regla nueva",
//       valor: indicadores.coberturaNueva,
//       meta: metas.cobertura,
//       tipo: "mayor",
//       mostrar: porcentaje,
//     },

//     {
//       nombre: "Absorción",
//       valor: null,
//       meta: null,
//       tipo: "mayor",
//       mostrar: () => "Pendiente",
//     },
//   ];

//   contenedor.innerHTML = indicadoresMeta
//     .map((item) => {
//       const estado = estadoMeta(item.valor, item.meta, item.tipo);

//       const valorTexto = item.mostrar(item.valor);

//       return `

//             <div class="traffic-item">

//                 <span>
//                     ${escaparHTML(item.nombre)}
//                     <small class="muted">
//                         ${
//                           item.meta === null
//                             ? ""
//                             : " · Meta: " +
//                               (item.nombre === "Promedio académico"
//                                 ? formatoNumero(item.meta, 2)
//                                 : item.nombre === "Alertados · regla nueva"
//                                   ? formatoNumero(item.meta)
//                                   : porcentaje(item.meta))
//                         }
//                     </small>
//                 </span>

//                 <span class="traffic-state ${estado.clase}">
//                     ${escaparHTML(valorTexto)} · ${estado.texto}
//                 </span>

//             </div>

//         `;
//     })
//     .join("");
// }

// =====================================================
// 11. TABLA DETALLADA
// =====================================================

function renderizarSemaforos(i) {
  const contenedor = elemento("trafficLights");
  if (!contenedor) return;

  const num = (v) => formatoNumero(v);
  const dec = (v) => formatoNumero(v, 2);

  const items = [
    ["Absorción", i.absorcion, metas.absorcion, "mayor", porcentaje],
    ["Retención", i.retencion, metas.retencion, "mayor", porcentaje],
    ["Deserción", i.desercion, metas.desercion, "menor", porcentaje],
    ["Promedio cohorte", i.promedio, metas.promedio, "mayor", dec],
    [
      "Alertados · regla actual",
      i.alertasActuales,
      metas.alertados,
      "menor",
      num,
    ],
    [
      "Precisión · regla actual",
      i.precisionActual,
      metas.precision,
      "mayor",
      porcentaje,
    ],
    [
      "Cobertura · regla actual",
      i.coberturaActual,
      metas.cobertura,
      "mayor",
      porcentaje,
    ],
    ["Alertados · regla nueva", i.alertasNuevas, metas.alertados, "menor", num],
    [
      "Precisión · regla nueva",
      i.precisionNueva,
      metas.precision,
      "mayor",
      porcentaje,
    ],
    [
      "Cobertura · regla nueva",
      i.coberturaNueva,
      metas.cobertura,
      "mayor",
      porcentaje,
    ],
  ];

  contenedor.innerHTML = items
    .map(([nombre, valor, meta, tipo, fmt]) => {
      const estado = estadoMeta(valor, meta, tipo);
      return `
            <div class="traffic-item">
                <span>${escaparHTML(nombre)}
                    <small class="muted"> · Meta: ${fmt(meta)}</small></span>
                <span class="traffic-state ${estado.clase}">
                    ${escaparHTML(fmt(valor))} · ${estado.texto}</span>
            </div>`;
    })
    .join("");
}

function renderizarTabla(filas) {
  const cuerpo = elemento("detailTable")?.querySelector("tbody");

  if (!cuerpo) return;

  if (!filas.length) {
    cuerpo.innerHTML = `
            <tr>
                <td colspan="8">
                    No hay resultados para los filtros seleccionados.
                </td>
            </tr>
        `;

    return;
  }

  const filasOrdenadas = [...filas].sort((a, b) => {
    const comparacion = a.programa.localeCompare(b.programa, "es");

    return (
      comparacion || a.estrato.localeCompare(b.estrato, "es", { numeric: true })
    );
  });

  cuerpo.innerHTML = filasOrdenadas
    .map((fila) => {
      const retencion = tasa(fila.matriculados, fila.cohorte);

      const desercion = tasa(fila.desertores, fila.cohorte);

      return `

            <tr>

                <td>${escaparHTML(fila.programa)}</td>

                <td>${escaparHTML(fila.estrato)}</td>

                <td>${formatoNumero(fila.cohorte)}</td>

                <td>${porcentaje(retencion)}</td>

                <td>${porcentaje(desercion)}</td>

                <td>${formatoNumero(fila.promedio, 2)}</td>

                <td>${formatoNumero(fila.alertasActuales)}</td>

                <td>${formatoNumero(fila.alertasNuevas)}</td>

            </tr>

        `;
    })
    .join("");
}

// =====================================================
// 12. ACTUALIZACIÓN GENERAL DEL TABLERO
// =====================================================

function actualizarTablero() {
  const filas = obtenerFilasFiltradas();

  const indicadores = calcularIndicadores(filas);

  renderizarMetricas(indicadores);

  renderizarGrafico(filas);

  renderizarSemaforos(indicadores);

  renderizarTabla(filas);
}

// =====================================================
// 13. ACTIVAR EVENTOS DE LOS FILTROS
// =====================================================

function iniciarFiltros() {
  const ids = ["programFilter", "facultyFilter", "stratumFilter"];

  ids.forEach((id) => {
    const control = elemento(id);

    if (!control) return;

    control.addEventListener("change", actualizarTablero);
  });

  const botonLimpiar = elemento("resetFilters");

  if (botonLimpiar) {
    botonLimpiar.addEventListener("click", () => {
      ids.forEach((id) => {
        const control = elemento(id);

        if (control) control.value = "";
      });

      actualizarTablero();
    });
  }
}

// =====================================================
// 14. VALIDACIÓN DE CONSISTENCIA
// =====================================================

function validarIntegridad() {
  const total = suma(registros, "cohorte");

  if (total !== DATA.metadata.totalEstudiantes) {
    console.warn(
      "Advertencia: el detalle agregado no coincide con el total de cohorte.",
      {
        totalDeclarado: DATA.metadata.totalEstudiantes,
        totalDetalle: total,
      },
    );
  }

  registros.forEach((fila) => {
    if (fila.matriculados + fila.desertores !== fila.cohorte) {
      console.warn(
        "Inconsistencia en matrícula/deserción:",
        fila.programa,
        fila.estrato,
      );
    }

    if (fila.promedio < 0 || fila.promedio > 5) {
      console.warn(
        "Promedio fuera de la escala 0–5:",
        fila.programa,
        fila.estrato,
        fila.promedio,
      );
    }

    if (fila.tpNueva > fila.alertasNuevas) {
      console.warn(
        "Verdaderos positivos mayores que alertas:",
        fila.programa,
        fila.estrato,
      );
    }
  });
}

// =====================================================
// 15. INICIALIZACIÓN
// =====================================================

document.addEventListener("DOMContentLoaded", () => {
  validarIntegridad();

  iniciarNavegacion();

  renderizarInicio();

  cargarFiltros();

  iniciarFiltros();

  actualizarTablero();

  console.info("Observatorio de Permanencia inicializado correctamente.");
});
