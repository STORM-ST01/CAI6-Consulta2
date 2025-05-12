import pulp
import csv
import os

# -------- DATOS (Adaptados para el enfoque multi-instancia) --------
ROLES_DEFINITIONS = {
    "JVG": {"id": 1, "rol_org": "DG"},
    "HYV": {"id": 2, "rol_org": "DR"}, # HYV también es TR
    "GTR": {"id": 3, "rol_org": "TR"},
    "LPG": {"id": 4, "rol_org": "TR"}, # LPG también es TC
    "RGB": {"id": 5, "rol_org": "TR"}, # RGB también es TC
    "BJC": {"id": 6, "rol_org": "TR"},
    "MDS": {"id": 7, "rol_org": "TC"},
    "PGR": {"id": 8, "rol_org": "DM"},
    "MFE": {"id": 9, "rol_org": "DE"},
    "HJR": {"id": 10, "rol_org": "PS"},
    "PTS": {"id": 11, "rol_org": "PS"},
    "IHP": {"id": 12, "rol_org": "PS"}
}

# Mapeo de ID de persona a nombre y viceversa
personas_id_to_name = {details["id"]: name for name, details in ROLES_DEFINITIONS.items()}
personas_name_to_id = {name: details["id"] for name, details in ROLES_DEFINITIONS.items()}
all_persona_ids = list(personas_id_to_name.keys())

# Definición de qué roles organizativos pueden hacer qué tareas
TAREAS_ROLES_ORG = {
    "T1": ["DR"],
    "T2.1": ["TR"],
    "T2.2": ["TC"],
    "T3": ["DM"],
    "T4": ["DE", "PS"]
}

# Lista de todas las tareas
tareas_list = list(TAREAS_ROLES_ORG.keys())

# Crear el mapeo de Tarea -> Lista de IDs de personas permitidas (considerando jerarquía y roles múltiples)
# Esta es una parte crucial que adapta la lógica de new_solver.py
tareas_personas_permitidas = {}
for tarea, roles_org_permitidos in TAREAS_ROLES_ORG.items():
    personas_para_tarea = set()
    for rol_org in roles_org_permitidos:
        for nombre_persona, details in ROLES_DEFINITIONS.items():
            # Caso base: rol organizativo directo
            if details["rol_org"] == rol_org:
                personas_para_tarea.add(details["id"])
            
            # Jerarquía y roles múltiples (simplificado, new_solver.py tenía esto más explícito)
            # DG (JVG) puede hacer todo lo de DR, DM, DE
            if rol_org in ["DR", "DM", "DE"] and details["rol_org"] == "DG":
                personas_para_tarea.add(personas_name_to_id["JVG"])
            # DR (HYV) puede hacer todo lo de TR, TC
            if rol_org in ["TR", "TC"] and details["rol_org"] == "DR":
                 personas_para_tarea.add(personas_name_to_id["HYV"])
            
            # Casos especiales para roles múltiples como LPG, RGB, HYV
            if rol_org == "TR" and nombre_persona in ["LPG", "RGB", "HYV"]: # HYV es DR y TR
                personas_para_tarea.add(personas_name_to_id[nombre_persona])
            if rol_org == "TC" and nombre_persona in ["LPG", "RGB"]: # LPG, RGB son TR y TC
                personas_para_tarea.add(personas_name_to_id[nombre_persona])

    tareas_personas_permitidas[tarea] = list(personas_para_tarea)

# Ajuste manual final basado en la lógica de new_solver.py para asegurar consistencia
# (Esta parte es para replicar exactamente la elegibilidad de new_solver.py)
tareas_personas_permitidas_final = {
    "T1": [personas_name_to_id["JVG"], personas_name_to_id["HYV"]],
    "T2.1": [personas_name_to_id[p] for p in ["JVG", "HYV", "GTR", "LPG", "RGB", "BJC"]],
    "T2.2": [personas_name_to_id[p] for p in ["JVG", "HYV", "LPG", "RGB", "MDS"]],
    "T3": [personas_name_to_id["JVG"], personas_name_to_id["PGR"]],
    "T4": [personas_name_to_id[p] for p in ["JVG", "MFE", "HJR", "PTS", "IHP"]]
}

NUM_INSTANCIAS = 20

# -------- MODELO PuLP (Global para todas las instancias) --------
model = pulp.LpProblem("Asignacion_Global_Tareas_BPMS", pulp.LpMinimize)

# Variables binarias: assign[k, tarea, persona_id]
assign = pulp.LpVariable.dicts(
    "assign",
    ((k, tarea_name, p_id) for k in range(NUM_INSTANCIAS) 
                             for tarea_name in tareas_list 
                             for p_id in all_persona_ids),
    cat="Binary"
)

# --------- RESTRICCIONES (Aplicadas a las NUM_INSTANCIAS) ---------

# 1. Cada tarea en cada instancia asignada a UN ÚNICO rol permitido
for k in range(NUM_INSTANCIAS):
    for tarea_name, roles_permitidos_ids in tareas_personas_permitidas_final.items():
        model += pulp.lpSum(assign[(k, tarea_name, p_id)] for p_id in roles_permitidos_ids) == 1, \
                 f"AsignacionUnica_{k}_{tarea_name}"
        # Adicional: asegurar que solo los permitidos puedan ser asignados (implícito si se suma sobre roles_permitidos_ids)
        for p_id_general in all_persona_ids:
            if p_id_general not in roles_permitidos_ids:
                model += assign[(k, tarea_name, p_id_general)] == 0, f"NoPermitido_{k}_{tarea_name}_{p_id_general}"


# 2. Cada persona como mucho realiza UNA tarea por instancia
for k in range(NUM_INSTANCIAS):
    for p_id in all_persona_ids:
        model += pulp.lpSum(assign[(k, tarea_name, p_id)] for tarea_name in tareas_list) <= 1, \
                 f"UnaTareaPorPersona_{k}_{p_id}"

# 3. R1: Separación de deberes entre T2.1 y T2.2
for k in range(NUM_INSTANCIAS):
    for p_id in all_persona_ids:
        model += assign[(k, "T2.1", p_id)] + assign[(k, "T2.2", p_id)] <= 1, \
                 f"SoD_T21_T22_{k}_{p_id}"

# 4. R2: Separación de deberes entre T3 y T4
for k in range(NUM_INSTANCIAS):
    for p_id in all_persona_ids:
        model += assign[(k, "T3", p_id)] + assign[(k, "T4", p_id)] <= 1, \
                 f"SoD_T3_T4_{k}_{p_id}"

# 5. R3: Binding - Si GTR (ID 3) realiza T2.1, MDS (ID 7) realiza T2.2
id_gtr = personas_name_to_id["GTR"]
id_mds = personas_name_to_id["MDS"]
for k in range(NUM_INSTANCIAS):
    model += assign[(k, "T2.1", id_gtr)] <= assign[(k, "T2.2", id_mds)], \
             f"Binding_GTR_MDS_{k}"

# 6. R4: JVG (ID 1) sólo puede participar en T1
id_jvg = personas_name_to_id["JVG"]
for k in range(NUM_INSTANCIAS):
    for tarea_name in ["T2.1", "T2.2", "T3", "T4"]:
        model += assign[(k, tarea_name, id_jvg)] == 0, \
                 f"JVG_Solo_T1_{k}_{tarea_name}"

# --------- OBJETIVO (Fairness R5 + T1 Balance) ---------
# R5: Minimizar la desviación de la participación promedio general
participacion = {p_id: pulp.lpSum(assign[(k, t_name, p_id)] 
                                for k in range(NUM_INSTANCIAS) 
                                for t_name in tareas_list) 
                 for p_id in all_persona_ids}

avg_participation_val = (NUM_INSTANCIAS * len(tareas_list)) / len(all_persona_ids)

desviaciones_generales = {p_id: pulp.LpVariable(f"desviacion_general_{p_id}", lowBound=0) 
                          for p_id in all_persona_ids}

for p_id in all_persona_ids:
    model += participacion[p_id] - avg_participation_val <= desviaciones_generales[p_id]
    model += avg_participation_val - participacion[p_id] <= desviaciones_generales[p_id]

# Componente para equilibrar T1 entre JVG (ID 1) y HYV (ID 2)
id_hyv = personas_name_to_id["HYV"]
count_T1_JVG = pulp.lpSum(assign[(k, "T1", id_jvg)] for k in range(NUM_INSTANCIAS))
T1_JVG_target_deviation = pulp.LpVariable("T1_JVG_target_dev", lowBound=0)
target_T1_assignments_for_JVG = NUM_INSTANCIAS / 2 # Idealmente 10 para JVG, 10 para HYV

model += count_T1_JVG - target_T1_assignments_for_JVG <= T1_JVG_target_deviation
model += target_T1_assignments_for_JVG - count_T1_JVG <= T1_JVG_target_deviation

# Objetivo combinado:
weight_T1_balance = 1.0 # Ajustar según necesidad (e.g., 10.0 para priorizar T1 balance)
model += pulp.lpSum(desviaciones_generales[p_id] for p_id in all_persona_ids) + \
         (weight_T1_balance * T1_JVG_target_deviation)

# -------- MAIN --------
if __name__ == "__main__":
    solver = pulp.PULP_CBC_CMD(msg=1, timeLimit=300) # msg=0 para menos output, timeLimit opcional
    model.solve(solver)

    output_dir = "sod_verification"
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "distribucion.csv")

    if model.status == pulp.LpStatusOptimal:
        print("\n✔️ Solución óptima encontrada.")
        with open(file_path, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Instancia", "T1", "T2.1", "T2.2", "T3", "T4"])

            for k_instance in range(NUM_INSTANCIAS):
                fila = [k_instance + 1]
                for tarea_name_csv in tareas_list:
                    asignado_en_tarea = False
                    for p_id_csv in tareas_personas_permitidas_final[tarea_name_csv]:
                        if pulp.value(assign[(k_instance, tarea_name_csv, p_id_csv)]) == 1:
                            fila.append(personas_id_to_name[p_id_csv])
                            asignado_en_tarea = True
                            break
                    if not asignado_en_tarea:
                        fila.append("ERROR_NO_ASIGNADO")
                writer.writerow(fila)
        print(f"\n✔️ ¡Instancias generadas y guardadas en '{file_path}' correctamente!")

        val_count_T1_JVG = pulp.value(count_T1_JVG)
        print(f"Conteo de T1 para JVG ({id_jvg}): {val_count_T1_JVG}")
        print(f"Conteo de T1 para HYV ({id_hyv}): {NUM_INSTANCIAS - val_count_T1_JVG}")

    elif model.status == pulp.LpStatusInfeasible:
        print("\n❌ El problema es infactible. No se encontró solución que cumpla todas las restricciones.")
    elif model.status == pulp.LpStatusUnbounded:
        print("\n❌ El problema es no acotado.")
    else:
        print(f"\n❓ Estado del solver: {pulp.LpStatus[model.status]}")