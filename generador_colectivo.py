import csv
import json
import os
import glob
import gc
import sys
import resource
from collections import defaultdict, namedtuple

EVENTOS_VALIDOS = {'333', '222', '444', '555', '666', '777', '333bf', '333oh', 'clock', 'minx', 'pyram', 'skewb', 'sq1', '444bf', '555bf'}

# NUEVO: tuplas con nombre en vez de dicts por solve -> mismo coste de memoria
# que una tupla normal (sin overhead por instacia), pero con acceso legible.
Solve = namedtuple('Solve', ['time', 'wca_id', 'pais', 'continente', 'comp_id', 'fecha', 'personName'])
ResultInfo = namedtuple('ResultInfo', ['ev', 'wca_id', 'pais', 'continente', 'comp_id', 'fecha', 'personName'])

def log_mem(etiqueta):
    # ru_maxrss está en KB en Linux
    mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(f"[MEM] {etiqueta}: {mem_mb:.0f} MB (pico acumulado)", flush=True)

def encontrar_archivo(nombre_base):
    patrones = [
        f"WCA_export_{nombre_base}.tsv",
        f"WCA_export_{nombre_base.lower()}.tsv",
        f"{nombre_base}.tsv",
        f"{nombre_base.lower()}.tsv"
    ]
    for p in patrones:
        if os.path.exists(p): return p
    coincidencias = glob.glob(f"*{nombre_base}*.tsv", recursive=False)
    if coincidencias: return coincidencias[0]
    coincidencias_min = glob.glob(f"*{nombre_base.lower()}*.tsv", recursive=False)
    if coincidencias_min: return coincidencias_min[0]
    return f"WCA_export_{nombre_base.lower()}.tsv"

# ── Función reutilizable para procesar un lote de solves ──────────────
def procesar_lote(solves_dict, sufijo_archivo, etiqueta, paises_continentes):
    for evento, solves in solves_dict.items():
        print(f"Calculando {etiqueta} {evento}... ({len(solves)} solves)", flush=True)
        solves.sort(key=lambda x: x.fecha)
        
        datos_colectivos = {
            'Metadata': {'paises_continentes': paises_continentes},
            'Mundial': {'tiempos': {}, 'hall_of_fame_individuals': defaultdict(int), 'hall_of_fame_countries': defaultdict(int), 'hall_of_fame_continents': defaultdict(int)},
            'Continental': defaultdict(lambda: {'tiempos': {}, 'hall_of_fame_individuals': defaultdict(int), 'hall_of_fame_countries': defaultdict(int)}),
            'Nacional': defaultdict(lambda: {'tiempos': {}, 'hall_of_fame_individuals': defaultdict(int)})
        }
        
        for s in solves:
            t = s.time
            p = s.pais
            c = s.continente
            persona = f"{s.personName} ({s.wca_id})"
            
            # --- MUNDIAL ---
            if t not in datos_colectivos['Mundial']['tiempos']:
                datos_colectivos['Mundial']['tiempos'][t] = {'fecha': s.fecha, 'descubridores': [persona], 'comps': [s.comp_id]}
                datos_colectivos['Mundial']['hall_of_fame_individuals'][persona] += 1
                datos_colectivos['Mundial']['hall_of_fame_countries'][p] += 1
                datos_colectivos['Mundial']['hall_of_fame_continents'][c] += 1
            elif s.fecha == datos_colectivos['Mundial']['tiempos'][t]['fecha'] and persona not in datos_colectivos['Mundial']['tiempos'][t]['descubridores']:
                datos_colectivos['Mundial']['tiempos'][t]['descubridores'].append(persona)
                datos_colectivos['Mundial']['tiempos'][t]['comps'].append(s.comp_id)
                datos_colectivos['Mundial']['hall_of_fame_individuals'][persona] += 1
                datos_colectivos['Mundial']['hall_of_fame_countries'][p] += 1
                datos_colectivos['Mundial']['hall_of_fame_continents'][c] += 1
                    
            # --- CONTINENTAL ---
            if t not in datos_colectivos['Continental'][c]['tiempos']:
                datos_colectivos['Continental'][c]['tiempos'][t] = {'fecha': s.fecha, 'descubridores': [persona], 'comps': [s.comp_id]}
                datos_colectivos['Continental'][c]['hall_of_fame_individuals'][persona] += 1
                datos_colectivos['Continental'][c]['hall_of_fame_countries'][p] += 1
            elif s.fecha == datos_colectivos['Continental'][c]['tiempos'][t]['fecha'] and persona not in datos_colectivos['Continental'][c]['tiempos'][t]['descubridores']:
                datos_colectivos['Continental'][c]['tiempos'][t]['descubridores'].append(persona)
                datos_colectivos['Continental'][c]['tiempos'][t]['comps'].append(s.comp_id)
                datos_colectivos['Continental'][c]['hall_of_fame_individuals'][persona] += 1
                datos_colectivos['Continental'][c]['hall_of_fame_countries'][p] += 1
                    
            # --- NACIONAL ---
            if t not in datos_colectivos['Nacional'][p]['tiempos']:
                datos_colectivos['Nacional'][p]['tiempos'][t] = {'fecha': s.fecha, 'descubridores': [persona], 'comps': [s.comp_id]}
                datos_colectivos['Nacional'][p]['hall_of_fame_individuals'][persona] += 1
            elif s.fecha == datos_colectivos['Nacional'][p]['tiempos'][t]['fecha'] and persona not in datos_colectivos['Nacional'][p]['tiempos'][t]['descubridores']:
                datos_colectivos['Nacional'][p]['tiempos'][t]['descubridores'].append(persona)
                datos_colectivos['Nacional'][p]['tiempos'][t]['comps'].append(s.comp_id)
                datos_colectivos['Nacional'][p]['hall_of_fame_individuals'][persona] += 1

        # SOrdenar halls of fame
        datos_colectivos['Mundial']['hall_of_fame_individuals'] = dict(sorted(datos_colectivos['Mundial']['hall_of_fame_individuals'].items(), key=lambda x: x[1], reverse=True))
        datos_colectivos['Mundial']['hall_of_fame_countries'] = dict(sorted(datos_colectivos['Mundial']['hall_of_fame_countries'].items(), key=lambda x: x[1], reverse=True))
        datos_colectivos['Mundial']['hall_of_fame_continents'] = dict(sorted(datos_colectivos['Mundial']['hall_of_fame_continents'].items(), key=lambda x: x[1], reverse=True))
        
        for c_key in datos_colectivos['Continental']:
            datos_colectivos['Continental'][c_key]['hall_of_fame_individuals'] = dict(sorted(datos_colectivos['Continental'][c_key]['hall_of_fame_individuals'].items(), key=lambda x: x[1], reverse=True))
            datos_colectivos['Continental'][c_key]['hall_of_fame_countries'] = dict(sorted(datos_colectivos['Continental'][c_key]['hall_of_fame_countries'].items(), key=lambda x: x[1], reverse=True))
            
        for p_key in datos_colectivos['Nacional']:
            datos_colectivos['Nacional'][p_key]['hall_of_fame_individuals'] = dict(sorted(datos_colectivos['Nacional'][p_key]['hall_of_fame_individuals'].items(), key=lambda x: x[1], reverse=True))

        nombre_archivo = f'collective{sufijo_archivo}_{evento}.json'
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            json.dump(datos_colectivos, f)

        del datos_colectivos # liberar antes del siguiente evento (333 puede ser muy grande)
    log_mem(f"Fin procesar_lote({etiqueta})")
# ─────────────────────────────────────────────────────────────────────

def procesar_datos():
    COMPETITIONS_FILE = encontrar_archivo("Competitions")
    COUNTRIES_FILE = encontrar_archivo("Countries")
    RESULTS_FILE = encontrar_archivo("Results")
    ATTEMPTS_FILE = encontrar_archivo("result_attempts") or encontrar_archivo("ResultAttempts")

    comps = {}
    print("Leyendo competiciones...", flush=True)
    with open(COMPETITIONS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            date_str = f"{row['year']}-{row['month'].zfill(2)}-{row['day'].zfill(2)}"
            comps[sys.intern(row['id'])] = date_str
    log_mem("Tras leer competiciones")

    paises_continentes = {}
    print("Mapeando continentes...", flush=True)
    with open(COUNTRIES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            paises_continentes[sys.intern(row['id'])] = sys.intern(row['continent_id'])
    log_mem("Tras mapear continentes")

    # ══════════════════════════════════════════════════════════════
    # FASE 1: SINGLES — se procesa y se libera ANTES de tocar medias.
    # No mantener ambos datasets vivos a la vez es la clave: Attempts.tsv
    # es la tabla más grande de todo el export WCA.
    # ══════════════════════════════════════════════════════════════
    print("\n=== FASE 1: SINGLES ===", flush=True)
    print("Procesando tabla principal de Results (singles)...", flush=True)
    resultados_brutos = defaultdict(list) # singles (intentos individuales)
    result_info = {}
    
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for i, row in enumerate(reader, 1):
            if i % 1_000_000 == 0:
                print(f"  ...{i:,} filas de Results leídas", flush=True)
                log_mem(f"Results fila {i:,}")

            ev = row['event_id']
            if ev not in EVENTOS_VALIDOS: continue
            
            res_id = row['id']
            # NUEVO: sys.intern() en campos que se repiten muchísimo entre filas
            wca_id = sys.intern(row['person_id'])
            pais = sys.intern(row['person_country_id'])
            continente = paises_continentes.get(pais, "Unknown")
            comp_id = sys.intern(row['competition_id'])
            fecha = comps.get(comp_id, "9999-99-99")
            pname = sys.intern(row['person_name'])
            
            # Memoria optimizada: Guardamos los datos estructurales del resultado
            result_info[res_id] = ResultInfo(ev, wca_id, pais, continente, comp_id, fecha, pname)
            
            # Singles: rescatar el 'best' oficial
            b = int(row.get('best', '0') or '0')
            if b > 0:
                resultados_brutos[ev].append(Solve(b, wca_id, pais, continente, comp_id, fecha, pname))

    log_mem("Tras leer Results (fase singles, antes de attempts)")
    print(f"Total resultados válidos indexados: {len(result_info):,}", flush=True)

    if ATTEMPTS_FILE and os.path.exists(ATTEMPTS_FILE):
        print(f"Procesando tabla secundaria de Intentos ({ATTEMPTS_FILE})...", flush=True)
        with open(ATTEMPTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for i, row in enumerate(reader, 1):
                if i % 2_000_000 == 0:
                    print(f"  ...{i:,} filas de Attempts leídas", flush=True)
                    log_mem(f"Attempts fila {i:,}")

                res_id = row['result_id']
                info = result_info.get(res_id)
                if info is not None:
                    val = row.get('value', '0')
                    if val.lstrip('-').isdigit():
                        v = int(val)
                        if v > 0:
                            resultados_brutos[info.ev].append(Solve(
                                v, info.wca_id, info.pais, info.continente,
                                info.comp_id, info.fecha, info.personName
                            ))
    else:
        print("AVISO: No se encontró la tabla result_attempts. Faltarán tiempos de singles.", flush=True)

    log_mem("Tras leer Attempts (fase singles completa)")
    result_info.clear()
    del result_info
    gc.collect()
    log_mem("Tras liberar result_info")

    procesar_lote(resultados_brutos, '', 'singles', paises_continentes)

    # Liberamos TODO lo de singles antes de empezar con medias
    resultados_brutos.clear()
    del resultados_brutos
    gc.collect()
    log_mem("Tras liberar dataset de singles por completo")

    # ══════════════════════════════════════════════════════════════
    # FASE 2: MEDIAS — relee Results.tsv desde cero. NO toca
    # result_attempts.tsv, así que es mucho más ligera en memoria
    # que la fase de singles.
    # ══════════════════════════════════════════════════════════════
    print("\n=== FASE 2: MEDIAS ===", flush=True)
    print("Procesando tabla principal de Results (medias)...", flush=True)
    resultados_brutos_avg = defaultdict(list)

    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for i, row in enumerate(reader, 1):
            if i % 1_000_000 == 0:
                print(f"  ...{i:,} filas de Results (medias) leídas", flush=True)
                log_mem(f"Results-avg fila {i:,}")

            ev = row['event_id']
            if ev not in EVENTOS_VALIDOS: continue

            avg_val = int(row.get('average', '0') or '0')
            if avg_val <= 0: continue

            wca_id = sys.intern(row['person_id'])
            pais = sys.intern(row['person_country_id'])
            continente = paises_continentes.get(pais, "Unknown")
            comp_id = sys.intern(row['competition_id'])
            fecha = comps.get(comp_id, "9999-99-99")
            pname = sys.intern(row['person_name'])

            resultados_brutos_avg[ev].append(Solve(avg_val, wca_id, pais, continente, comp_id, fecha, pname))

    log_mem("Tras leer Results (fase medias completa)")

    procesar_lote(resultados_brutos_avg, '_avg', 'medias', paises_continentes)

    resultados_brutos_avg.clear()
    del resultados_brutos_avg
    gc.collect()
    log_mem("Tras liberar dataset de medias")
            
    print("\n¡Completado!", flush=True)

if __name__ == "__main__":
    procesar_datos()