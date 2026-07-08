# MEMORIA DEL PROYECTO — mifuturo-datos

> Datos de Educación Superior de Chile (SIES / MINEDUC)
> Fuente: https://www.mifuturo.cl/sies/

---

## Sesiones

### [2026-06-22] — Inicial: Descarga de datasets

**Qué se hizo:**
- Se exploró el portal mifuturo.cl, sección SIES → Bases de Datos
- Se descargaron los **5 datasets históricos** + sus **glosarios/metodologías**

**Archivos descargados:**

| Categoría | Archivo | Tamaño | Cobertura |
|---|---|---|---|
| Matrícula | `matricula/matricula_historica_2007_2025.zip` | 15 MB | 2007–2025 |
| Matrícula | `matricula/glosario_matricula.pdf` | 179 KB | — |
| Titulación | `titulacion/titulados_historico_2007_2025.xlsx` | 39 MB | 2007–2025 |
| Titulación | `titulacion/glosario_titulados.pdf` | 259 KB | — |
| Personal Académico | `personal-academico/personal_academico_historico_2008_2025.xlsx` | 2.1 MB | 2008–2025 |
| Personal Académico | `personal-academico/glosario_personal_academico.pdf` | 182 KB | — |
| Oferta Académica | `oferta-academica/oferta_academica_historica_2010_2026.xlsx` | 88 MB | 2010–2026 |
| Oferta Académica | `oferta-academica/glosario_oferta_academica.pdf` | 477 KB | — |
| Buscador Carreras | `buscadores/buscador_carreras_2025_2026.xlsx` | 3.0 MB | 2025–2026 |
| Buscador Carreras | `buscadores/metodologia_buscador_carreras.pdf` | 162 KB | — |
| Buscador Estadísticas | `buscadores/buscador_estadisticas_carrera_2025_2026.xlsx` | 73 KB | 2025–2026 |
| Buscador Estadísticas | `buscadores/metodologia_estadisticas_carrera.pdf` | 243 KB | — |
| Buscador Empleabilidad | `buscadores/buscador_empleabilidad_ingresos_2025_2026.xlsx` | 291 KB | 2025–2026 |
| Buscador Empleabilidad | `buscadores/metodologia_empleabilidad_ingresos.pdf` | 241 KB | — |
| Buscador Instituciones | `buscadores/buscador_instituciones_2025_2026.xlsx` | 127 KB | 2025–2026 |
| Buscador Instituciones | `buscadores/metodologia_buscador_instituciones.pdf` | 227 KB | — |

**Total:** 22 archivos | ~149 MB

|**Pendiente / Próximos pasos:**
|- *Definir objetivo del proyecto (pendiente desde el usuario)*

### [2026-06-22] — Investigación: Indicadores y KPIs de Educación Superior en Chile

**Qué se hizo:**
- Investigación web sobre los indicadores y KPIs que se miden en educación superior chilena
- Se identificaron las principales fuentes oficiales y sus respectivos marcos de indicadores

**Fuentes de indicadores identificadas:**

| Fuente | Organismo | Qué mide |
|---|---|---|
| SIES (mifuturo.cl) | Subsec. Educación Superior | 12 informes anuales + bases de datos |
| INDICES | CNED | Matrícula, retención, planta académica, infraestructura |
| CNA | Comisión Nacional de Acreditación | Acreditación institucional y de carreras |
| Superintendencia ES | Superintendencia | Salud financiera de IES |
| DIPRES | Ministerio de Hacienda | Indicadores de desempeño presupuestario |
| OECD (EAG) | OCDE | Comparación internacional (acceso, titulación, financiamiento, empleo) |

**Indicadores y KPIs por dimensión:**

**1. ACCESO Y COBERTURA**
| KPI | Descripción | Fuente |
|---|---|---|
| Tasa de cobertura ES (18-24 años) | % de jóvenes en edad teórica que accede a ES | MINEDUC / OECD |
| Matrícula total por nivel | Total matriculados pregrado, posgrado, postítulo | SIES |
| Matrícula 1er año | Nuevos ingresos al sistema | SIES |
| Matrícula por tipo de institución | Distribución: Univ, IP, CFT | SIES / CNED |
| Matrícula por región | Distribución geográfica | SIES / CNED |
| Matrícula por sexo | Participación femenina/masculina | SIES / CNED |
| Matrícula extranjera | Estudiantes internacionales | SIES |
| Participación personas con discapacidad | % con discapacidad registrada | SIES |
| Vías de acceso | % ingreso regular, PACE, BEA, admisión especial | Instituciones |

**2. TRAYECTORIA Y PERMANENCIA**
| KPI | Descripción | Fuente |
|---|---|---|
| Tasa de retención 1er año | % estudiantes que continúan al 2do año (por cohorte) | SIES / CNED |
| Tasa de retención por institución | Retención desagregada por IES | SIES / CNED |
| Deserción | % que abandona el sistema (complemento de retención) | SIES |
| Avance curricular | Créditos aprobados vs. inscritos | SIES |

**3. TITULACIÓN Y EFICIENCIA**
| KPI | Descripción | Fuente |
|---|---|---|
| Tasa de titulación total | Titulados totales por año | SIES |
| Tasa de titulación oportuna | % titulados en duración formal +1 año (~16% Chile) | SIES / OECD |
| Duración real de carreras | Semestres reales cursados vs. formales | SIES |
| Sobreduración | % estudiantes que exceden duración formal | SIES |
| Titulación por área del conocimiento | Distribución de titulados por disciplina | SIES |
| Eficiencia académica | Titulados / Matriculados en tiempo teórico | SIES |

**4. EMPLEABILIDAD E INGRESOS**
| KPI | Descripción | Fuente |
|---|---|---|
| Tasa de empleabilidad 1er año | % ocupados al año de titularse | SIES / Buscadores |
| Tasa de empleabilidad 2do año | % ocupados a los 2 años | SIES |
| Ingreso promedio 1er año | Ingresos al año de titulación | SIES |
| Ingreso promedio 4to año | Ingresos a los 4 años de titulación | SIES |
| Tasa de empleabilidad por carrera | Por programa específico | Buscador empleabilidad |
| Relación ingreso ES / costo | Retorno económico de la inversión | SIES / OECD |
| Tasa de empleo ES vs. no ES | Brecha laboral por nivel educativo | OECD |

**5. CUERPO ACADÉMICO**
| KPI | Descripción | Fuente |
|---|---|---|
| JCE (Jornada Completa Equivalente) | Cantidad de académicos | SIES |
| Jerarquía académica | Distribución jerarquías (titular, asociado, etc.) | SIES |
| Horas docente vs investigación | Distribución de dedicación | SIES |
| Estudios de postgrado | % académicos con doctorado / magíster | SIES |
| Tasa estudiantes por docente | Ratio estudiante / JCE | CNED / SIES |

**6. CALIDAD Y ASEGURAMIENTO**
| KPI | Descripción | Fuente |
|---|---|---|
| Acreditación institucional | Años de acreditación (desde 2 hasta 7 años) | CNA |
| Acreditación de carreras | Carreras acreditadas / no acreditadas | CNA |
| Años de acreditación | Nivel (2, 3, 4, 5, 6, 7 años) | CNA |
| Áreas acreditadas obligatorias | Medicina, Pedagogía, etc. | CNA |

**7. FINANCIAMIENTO**
| KPI | Descripción | Fuente |
|---|---|---|
| Gasto en ES como % del PIB | Inversión nacional en ES | OECD / DIPRES |
| Gasto público vs. privado | Distribución del financiamiento | OECD |
| Arancel real y arancel de referencia | Costos de carreras | MINEDUC |
| Beneficios estudiantiles | Cobertura de gratuidad, becas, créditos | MINEDUC |
| Salud financiera de IES | Indicadores contables y financieros | Superintendencia ES |

**8. EQUIDAD Y GÉNERO**
| KPI | Descripción | Fuente |
|---|---|---|
| Brecha de género en matrícula | % mujeres / hombres por área | SIES / CNED |
| Participación femenina en STEM | % mujeres en ciencia, tecnología, ingeniería, matemáticas | SIES |
| Brecha salarial por género | Diferencia ingresos hombres/mujeres titulados | SIES |
| Matrícula por grupo socioeconómico | Acceso por quintil / NSE | MINEDUC |
| Movilidad regional | Flujo estudiantes entre regiones | SIES |

**9. OFERTA ACADÉMICA**
| KPI | Descripción | Fuente |
|---|---|---|
| N° carreras por institución | Oferta total de programas | SIES |
| Distribución por área CINE/Unesco | Clasificación de programas | SIES |
| Oferta por modalidad | Presencial, semi-presencial, distancia/virtual | SIES |
| Oferta por región | Programas disponibles por zona | SIES |

**10. COMPARATIVOS INTERNACIONALES (OECD)**
| KPI | Descripción |
|---|---|
| Tasa de titulación ES (25-34 años) | % población joven con ES completa |
| Tasa de empleo por nivel educativo | Brecha empleo ES vs secundaria |
| Prima salarial ES | Diferencia ingresos ES vs secundaria |
| Movilidad estudiantil internacional | Estudiantes chilenos en el extranjero / extranjeros en Chile |
| Gasto por estudiante ES | Inversión por alumno |

**Nota:** Chile tiene la tasa de titulación oportuna más baja entre países OECD (~16%). La tasa de deserción supera el 23%. El acceso al sistema alcanza ~50% entre jóvenes.

---

### [2026-06-22] — Análisis de factibilidad: ¿Qué podemos construir con los datos descargados?

**Objetivo:** Acotar el proyecto solo a datasets SIES que ya tenemos descargados.

#### 1. MATRÍCULA (`matricula_historica_2007_2025.zip` → CSV, ~145 MB, 59 columnas)

**Granularidad:** cada fila = una carrera × sede × año (2007-2025)

| Campo | Uso potencial |
|---|---|
| AÑO, TOTAL MATRÍCULA, 1er AÑO, por género | Evolución matrícula total, crecimiento anual |
| CLASIFICACIÓN INSTITUCIÓN N1/N2/N3 | Distribución Univ / IP / CFT |
| REGIÓN, PROVINCIA, COMUNA | Distribución geográfica, mapas |
| NOMBRE CARRERA, ÁREA CONOCIMIENTO, CINE-F 97/13 | Matrícula por disciplina |
| MODALIDAD, JORNADA | Presencial vs distancia, diurna vs vespertina |
| ACREDITACIÓN INSTITUCIONAL/CARRERA | Calidad de la oferta |
| RANGOS DE EDAD, PROMEDIO EDAD | Perfil etario estudiantes |
| TES (MUNICIPAL, SUBVENCIONADO, PAGADO) | Origen escolar (equidad) |
| DURACIÓN CARRERA | Estructura programas |

**KPIs factibles:**
- ✅ Matrícula total por año (nacional)
- ✅ Cobertura: matrícula 1er año vs total
- ✅ Participación femenina (global y por área/disciplina)
- ✅ Distribución por tipo de institución (Univ/IP/CFT)
- ✅ Distribución geográfica (regional, provincial)
- ✅ Matrícula por modalidad y jornada
- ✅ Perfil etario de matriculados
- ✅ Origen escolar (equidad: % de estudiantes de establecimientos municipales vs pagados)
- ✅ Ranking de carreras e instituciones por matrícula

#### 2. TITULACIÓN (`titulados_historico_2007_2025.xlsx`, 234K filas, 42 columnas)

**Granularidad:** cada fila = un programa × año (2007-2025)

**KPIs factibles:**
- ✅ Titulación total por año (nacional)
- ✅ Titulación por género
- ✅ Distribución por tipo IES, área del conocimiento, región
- ✅ Titulación por modalidad y jornada
- ✅ Edad promedio al titularse
- ✅ Ranking carreras con más/menos titulados

#### 3. PERSONAL ACADÉMICO (`personal_academico_historico_2008_2025.xlsx`, 2.7K filas, 65 columnas)

**KPIs factibles:**
- ✅ N° de académicos por institución, tipo, año
- ✅ JCE (Jornada Completa Equivalente)
- ✅ Nivel de formación (doctores, magíster, profesionales)
- ✅ Distribución etaria
- ✅ Distribución por nacionalidad
- ✅ Ratio estudiantes / académico (cruzando con matrícula)

#### 4. OFERTA ACADÉMICA (`oferta_academica_historica_2010_2026.xlsx`, 396K filas, 69 columnas)

**KPIs factibles:**
- ✅ N° de carreras por año, tipo IES, región
- ✅ Aranceles (promedio, mediana, distribución)
- ✅ Vacantes ofrecidas
- ✅ Ponderaciones PAES y NEM requeridas
- ✅ Clasificación CINE/Unesco de la oferta
- ✅ Vigencia de programas

#### 5. BUSCADOR CARRERAS (XLSX, 2 hojas — datos reales por programa)

**KPIs factibles:**
- ✅ Arancel anual 2026 por carrera/institución
- ✅ Matrícula femenina y masculina total y 1er año (2025)
- ✅ Titulación 2024 por género
- ✅ Rango y promedio PAES de ingresantes
- ✅ Promedio NEM de ingresantes
- ✅ Vacantes 1er semestre
- ✅ Origen escolar (% municipal, subvencionado, pagado)

#### 6. BUSCADOR INSTITUCIONES (XLSX, 126 filas, 97 columnas)

**KPIs factibles:**
- ✅ Información financiera de IES (estados financieros 2024)
- ✅ Matrícula pregrado y posgrado
- ✅ Retención de pregrado (por IES)
- ✅ Duración programas pregrado
- ✅ JCE y personal académico
- ✅ Infraestructura y equipamiento

#### ⚠️ Indicadores que NO podemos calcular directamente con lo que tenemos

| Indicador | Dónde está | ¿Descargable? |
|---|---|---|
| Retención 1er año (tasa nacional, por cohorte) | Informe SIES "Retención de 1er año" | ✅ Sí — informes anuales en mifuturo.cl |
| Duración Real y Sobreduración | Informe SIES "Duración Real" | ✅ Sí |
| Matrícula Extranjera | Informe SIES específico | ✅ Sí |
| Movilidad Regional | Informe SIES específico | ✅ Sí |
| Avance Curricular | Informe SIES específico | ✅ Sí |
| Infraestructura y Recursos | Informe SIES | ✅ Sí (parcial en Buscador Instituciones) |
| Titulación oportuna | Requiere cruce cohorte ingreso vs titulación | ⚠️ No directo de nuestros datasets |

#### 📊 Foco recomendado

Con **lo que ya tenemos** podemos construir un sistema de indicadores robusto centrado en **4 pilares**:

1. **ACCESO Y COBERTURA** (Matrícula + Oferta Académica + Buscador Carreras)
2. **EFICIENCIA INTERNA** (Titulación + Matrícula) → relación titulados/matriculados
3. **CUERPO ACADÉMICO** (Personal Académico + Matrícula)
4. **MERCADO Y PONDERACIONES** (Buscador Carreras + Buscador Instituciones)

**Para complementar**, se descargaron los 6 informes pendientes desde SIES (ver sección siguiente).

---

### [2026-06-22] — Descarga y análisis de datasets complementarios SIES

Se descargaron 6 nuevos datasets desde mifuturo.cl:

| Dataset | Archivo | Tamaño | Hojas | Cobertura |
|---|---|---|---|---|
| 📊 Retención 1er año | `retencion/Informe_Retencion_SIES_2025.xlsx` | 313 KB | 7 | Cohortes 2007–2024 |
| ⏱ Duración Real y Sobreduración | `duracion-real/Duracion_Real_y_en-Exceso_SIES_2025.xlsx` | 626 KB | 10 | 2007–2024 |
| 🌍 Matrícula Extranjera | `extranjera/Matricula_Extranjera_2025_SIES.xlsx` | 85 KB | 3 | 2014–2024 |
| 🚪 Acceso a Educación Superior | `acceso/Acceso_Educacion_Superior_2025_SIES.xlsx` | 212 KB | 5 | Cohortes 2006–2024 |
| 📈 Avance Curricular | `avance-curricular/Avance_Curricular_SIES_2025.xlsx` | 158 KB | 5 | 2016–2024 |
| 🏗 Infraestructura y Recursos | `infraestructura/Infraestructura_2025.xlsx` | 115 KB | 4 | 2024–2025 |

#### Estructura y contenido

**1. RETENCIÓN 1er AÑO** — Formato wide (años como columnas)
| Hoja | Contenido |
|---|---|
| Retención 1er año general | Evolución por tipo IES (CFT/IP/Univ) 2007-2024 |
| Retención 1er año Carreras | Top 20 carreras genéricas por tipo IES |
| Retención 1er año Sexo | Por género |
| Retención 1er año Origen Sec. | Por tipo de establecimiento secundario |
| Retención 1er año x IES | Por institución individual (código + nombre) |

➡ **Indicadores clave:** Tasa de retención 1er año (nacional, por tipo IES, por carrera, por institución)

**2. DURACIÓN REAL Y SOBREDURACIÓN** — Formato wide
| Hoja | Contenido |
|---|---|
| Duración Real Pregrado | Semestres promedio por tipo IES (2007-2024) |
| Duración Real Posgrado / Postítulo | Semestres promedio |
| Duración en Exceso | Semestres adicionales |
| Sobreduración de las carreras | % sobreduración por nivel de formación |
| Duración Real Instituciones | Por institución individual (2010-2024) |
| DR y DEE por Sexo | Por género |

➡ **Indicadores clave:** Duración real (semestres), duración en exceso, % sobreduración

**3. MATRÍCULA EXTRANJERA** — Formato tabular
| Hoja | Contenido |
|---|---|
| Extranjeras_os Regulares | Matrícula extranjera por año (2014-2024), nacionalidad |
| Extranjeras_os Intercambio | Estudiantes de intercambio por región del mundo |
| Extranjeros por institución | Código IES, nombre, extranjeros regulares e intercambio |

➡ **Indicadores clave:** Matrícula extranjera total, por nacionalidad, por institución, intercambio

**4. ACCESO EDUCACIÓN SUPERIOR** — Formato wide
| Hoja | Contenido |
|---|---|
| Acceso Inmediato a ES | % acceso inmediato por género (cohortes 2006-2024) |
| Tipos IES a las que acceden | Distribución por tipo IES |
| Acceso Acumulado a ES | Matrícula acumulada por cohorte egreso EM (2015-2024) |
| Participación Acumulada | Por tipo IES en acceso acumulado |

➡ **Indicadores clave:** Tasa de acceso inmediato (%), acceso acumulado, brecha de género

**5. AVANCE CURRICULAR** — Formato tabular + wide
| Hoja | Contenido |
|---|---|
| Antecedentes | Matrícula con asignaturas vs créditos SCT |
| Aprobación Anual | Tasa de aprobación anual por tipo IES |
| Evolución Aprobación Anual | 2016-2024 |
| Avance Curricular Esperado | % avance por tipo IES |
| Evolución Avance Curricular Es. | Evolución por tipo IES 2016-2024 |

➡ **Indicadores clave:** Tasa de aprobación anual, avance curricular esperado

**6. INFRAESTRUCTURA**
| Hoja | Contenido |
|---|---|
| Cifras por región | m² construidos por región y tipo IES (2024-2025) |
| Evolución Inmuebles | Inmuebles de uso permanente 2015-2025 |
| Evolución Bibliotecas | Bibliotecas y colecciones 2015-2025 |
| Listado de Instituciones | m² por institución individual |

➡ **Indicadores clave:** m² construidos por IES/región, evolución de inmuebles y bibliotecas

#### 📊 Resumen: Sistema completo de indicadores SIES

Con los **12 datasets** ahora disponibles (6 originales + 6 complementarios), el cubrimiento es casi total:

| Pilar | Datasets fuente | Indicadores disponibles |
|---|---|---|
| **Acceso y Cobertura** | Matrícula + Oferta + Acceso ES + Extranjera | ✅ Cobertura bruta, acceso inmediato, acceso acumulado, matrícula extranjera, cobertura TES |
| **Trayectoria y Permanencia** | Retención + Avance Curricular | ✅ Retención 1er año (por IES/carrera/género/origen), aprobación anual, avance curricular |
| **Eficiencia Académica** | Titulación + Duración Real | ✅ Titulación total, duración real, sobreduración, duración en exceso |
| **Cuerpo Académico** | Personal Académico | ✅ JCE, nivel formación, ratio estudiante/académico |
| **Calidad** | Oferta (acreditación) + Buscador Instituciones | ✅ Acreditación institucional y de carreras |
| **Empleabilidad** | Buscador Carreras + Buscador Empleabilidad | ✅ Empleabilidad e ingresos (por buscador) |
| **Infraestructura** | Infraestructura | ✅ m² construidos, bibliotecas, evolución |
| **Equidad** | Matrícula + Acceso ES + Retención | ✅ Género, origen escolar, brechas, acceso |

---

## Notas técnicas

### Formato de los archivos
- **Matrícula**: ZIP con CSV dentro (2007–2025), 59 columnas, encoding latin-1
- **Titulación**: XLSX (2007–2025), 42 columnas
- **Personal Académico**: XLSX (2008–2025), estructura de bloques
- **Oferta Académica**: XLSX (2010–2026), 69 columnas
- **Buscadores**: XLSX + PDF de metodología
- **Informes complementarios (Retención, Duración, etc.)**: XLSX con múltiples hojas, formato wide (años como columnas), con filas de título/notas antes de los datos

### Cita requerida por la fuente
> *"FUENTE: www.mifuturo.cl, de Mineduc."*
> Si hay elaboración propia: *"FUENTE: Elaboración propia a partir de base publicada en www.mifuturo.cl"*

---

### [2026-07-01] — Estado del proyecto + Factibilidad OpenMetadata

**Qué se hizo:**
- Se retomó el proyecto SIES después de varias semanas
- Se verificó que `app.py` (dashboard Streamlit) está funcional y corriendo en http://localhost:8501
- Se investigó la factibilidad de incorporar **OpenMetadata** como plataforma de catálogo/gobernanza de datos

**Estado actual del proyecto:**

| Componente | Estado |
|---|---|
| Base SQLite (`mifuturo_sies.db`, 590 MB, 13 tablas, ~925K filas) | ✅ Lista |
| Dashboard Streamlit (`app.py`, 623 líneas) | ✅ Funcional en http://localhost:8501 |
| KPIs: Matrícula, Titulación, % Mujeres, Retención | ✅ Integrados |
| Gráficos: evolución histórica, tipo IES, área, región, empleabilidad | ✅ Integrados |
| Diseño: modo oscuro/claro, paleta institucional azul/dorado | ✅ Implementado |

**Datasets SIES actualmente descargados (11):**
1. Matrícula (2007–2025)
2. Titulación (2007–2025)
3. Personal Académico (2008–2025)
4. Oferta Académica (2010–2026)
5. Buscador Carreras (2025–2026)
6. Buscador Estadísticas Carrera (2025–2026)
7. Buscador Empleabilidad e Ingresos (2025–2026)
8. Buscador Instituciones (2025–2026)
9. Retención 1er año
10. Duración Real y Sobreduración
11. Matrícula Extranjera
12. Acceso a Educación Superior
13. Avance Curricular
14. Infraestructura y Recursos Educacionales

**Datasets faltantes por descargar para completar el proyecto:**

| Dataset | URL / Detalle | Tipo |
|---|---|---|
| Movilidad Regional 2025 | `mifuturo.cl/wp-content/uploads/2025/12/Movilidad-Regional-2025_Anexo-13112025.xlsx` | XLSX con anexo de datos |
| Brechas de Género 2025 | `mifuturo.cl/wp-content/uploads/2026/03/Brechas_de_Genero_2025.xlsx` | XLSX |
| Información Financiera | Varios XLSX históricos (2014–2019) en mifuturo.cl. Desde 2020 migró a Superintendencia ES | XLSX |
| Reportes DIVIA | Por explorar en mifuturo.cl | Probablemente PDF + anexos |
| Fichas Regionales | Por explorar | Probablemente PDF + anexos |
| Compendio Histórico | Por explorar | PDF |
| Reportes SIES | Por explorar | PDF |

**Factibilidad OpenMetadata:**

| Aspecto | Evaluación |
|---|---|
| Conector SQLite | ✅ OpenMetadata tiene conector nativo a SQLite |
| Docker | ✅ Instalado (v28.3.2 + Docker Compose v2.38.2) pero **motor detenido** — requiere inicio manual desde Docker Desktop |
| Recursos mínimos | 6 GB RAM + 4 vCPUs para el stack completo (OM server + MySQL/PostgreSQL + Elasticsearch + Airflow) |
| Beneficios potenciales | Catálogo de 20+ tablas, glosario de negocios, data profiler, data quality, lineage SIES → SQLite → Streamlit |
| Overhead | Stack pesado para proyecto personal de 1 DB + 1 dashboard |
| Alternativa ligera | Script Python de auto-documentación que genere catálogo HTML/Markdown desde la DB |
| Próximo paso | Iniciar Docker Desktop manualmente para desplegar OpenMetadata vía `docker compose up` |

**Próximos pasos pendientes:**
1. Descargar datasets faltantes (Movilidad Regional, Brechas de Género, Info. Financiera)
2. Integrar nuevos datos a la SQLite unificada
3. Iniciar Docker Desktop manualmente → desplegar OpenMetadata
4. Conectar SQLite a OpenMetadata → catalogar tablas + columnas
5. Crear glosario de negocios con KPIs de educación superior
6. Configurar Data Profiler y Data Quality tests
7. Integrar metadata en el dashboard Streamlit
