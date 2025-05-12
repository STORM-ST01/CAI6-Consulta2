import pulp
import csv
import os

# --------- DATOS ---------
# ID -> Nombre de persona
roles = {
    1: "JVG", 2: "HYV", 3: "GTR", 4: "LPG", 5: "RGB", 
    6: "BJC", 7: "MDS", 8: "PGR", 9: "MFE", 10: "HJR", 
    11: "PTS", 12: "IHP"
}

# Tareas y roles permitidos (ajustado según jerarquía)
# JVG (1, DG), HYV (2, DR), GTR (3, TR), LPG (4, TR/TC), RGB (5, TR/TC), 
# BJC (6, TR), MDS (7, TC), PGR (8, DM), MFE (9, DE), 
# HJR (10, PS), PTS (11, PS), IHP (12, PS)
tareas = {
    "T1": [1, 2],                 # DG (JVG), DR (HYV)
    "T2.1": [1, 2, 3, 4, 5, 6],   # DG, DR, TRs (GTR, LPG, RGB, BJC)
    "T2.2": [1, 2, 4, 5, 7],      # DG, DR, TCs (LPG, RGB, MDS) - MDS is 7
    "T3": [1, 8],                 # DG (JVG), DM (PGR)
    "T4": [1, 9, 10, 11, 12]      # DG (JVG), DE (MFE), PSs (HJR, PTS, IHP)
}

# --------- MODELO ---------
prob = pulp.LpProblem("Asignacion_Tareas_Offline", pulp.LpMinimize)

# Variables binaria: assign[k, tarea, rol]
assign = pulp.LpVariable.dicts(
    "assign",
    ((k, tarea, rol) for k in range(20) for tarea in tareas for rol in roles),
    cat="Binary"
)

# --------- RESTRICCIONES ---------

# Cada tarea en cada instancia asignada a un único rol permitido
for k in range(20):
    for tarea_name, roles_permitidos_list in tareas.items():
        # Ensure only roles from the specific list for that task are considered
        prob += pulp.lpSum(assign[(k, tarea_name, rol_id)] for rol_id in roles_permitidos_list) == 1

# Cada persona como mucho realiza una tarea por instancia
for k in range(20):
    for rol_id in roles:
        prob += pulp.lpSum(assign[(k, tarea_name, rol_id)] for tarea_name in tareas) <= 1

# R1: Separación de deberes entre T2.1 y T2.2
for k in range(20):
    for rol_id in roles:
        prob += assign[(k, "T2.1", rol_id)] + assign[(k, "T2.2", rol_id)] <= 1

# R2: Separación de deberes entre T3 y T4
for k in range(20):
    for rol_id in roles:
        prob += assign[(k, "T3", rol_id)] + assign[(k, "T4", rol_id)] <= 1

# R3: Binding - Si GTR (3) realiza T2.1, MDS (7) realiza T2.2
# This means: if assign[(k, "T2.1", 3)] is 1, then assign[(k, "T2.2", 7)] must be 1.
# Combined with the "one person per task" rule, this ensures MDS is the one doing T2.2.
for k in range(20):
    prob += assign[(k, "T2.1", 3)] <= assign[(k, "T2.2", 7)]

# R4: JVG (1) sólo puede participar en T1
for k in range(20):
    for tarea_name in ["T2.1", "T2.2", "T3", "T4"]: # Tasks JVG cannot do
        prob += assign[(k, tarea_name, 1)] == 0
    # Optional: Explicitly allow JVG in T1 if not covered by above (though T1 is not in the list)
    # This is implicitly handled as JVG is in tareas["T1"] and not restricted from it.

# --------- OBJETIVO (Fairness R5 + T1 Balance) ---------
# R5: Minimizar la desviación de la participación promedio general
participacion = {rol_id: pulp.lpSum(assign[(k, tarea_name, rol_id)] for k in range(20) for tarea_name in tareas) for rol_id in roles}

# Calculate average participation as a constant float for the objective
# Total tasks = 20 instances * 5 tasks/instance = 100
# Number of roles = len(roles)
avg_participation_val = (20 * len(tareas)) / len(roles)


# Variables auxiliares para las desviaciones absolutas de participación general
desviaciones_generales = {rol_id: pulp.LpVariable(f"desviacion_general_{rol_id}", lowBound=0) for rol_id in roles}

for rol_id in roles:
    prob += participacion[rol_id] - avg_participation_val <= desviaciones_generales[rol_id]
    prob += avg_participation_val - participacion[rol_id] <= desviaciones_generales[rol_id]

# Componente para equilibrar T1 entre JVG (1) y HYV (2)
# Target: cada uno hace T1 en 10 de las 20 instancias
count_T1_JVG = pulp.lpSum(assign[(k, "T1", 1)] for k in range(20))

# Variable para la desviación de JVG en T1 del objetivo de 10 instancias
T1_JVG_target_deviation = pulp.LpVariable("T1_JVG_target_dev", lowBound=0)
target_T1_assignments_for_JVG = 10 # Target 10 for JVG, implies 10 for HYV

prob += count_T1_JVG - target_T1_assignments_for_JVG <= T1_JVG_target_deviation
prob += target_T1_assignments_for_JVG - count_T1_JVG <= T1_JVG_target_deviation

# Objetivo combinado: Minimizar suma de desviaciones generales + desviación del balance de T1
# Weights can be adjusted if one part of the objective is more important.
# Using a weight for T1 deviation to make it more or less important relative to general fairness.
weight_T1_balance = 1.0 # Adjust as needed
prob += pulp.lpSum(desviaciones_generales[rol_id] for rol_id in roles) + (weight_T1_balance * T1_JVG_target_deviation)

# --------- SOLVER ---------
solver = pulp.PULP_CBC_CMD(msg=1) # msg=0 para menos output
prob.solve(solver)

# --------- EXPORTAR A CSV ---------
if prob.status == pulp.LpStatusOptimal:
    print("\n✔️ Solución óptima encontrada.")
    output_dir = "sod_verification"
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "new_instancias_bpmn.csv")

    with open(file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Instancia", "T1", "T2.1", "T2.2", "T3", "T4"])

        for k_instance in range(20): # k_instance from 0 to 19
            fila = [k_instance + 1] # Instancia numbers 1 to 20
            for tarea_name_csv in ["T1", "T2.1", "T2.2", "T3", "T4"]:
                asignado_en_tarea = False
                # Iterate through roles_permitidos_list for the current task to find the assignee
                # This ensures we only check relevant roles for the task
                roles_permitidos_for_task = tareas[tarea_name_csv]
                for rol_id_csv in roles_permitidos_for_task: 
                    if rol_id_csv in roles: # Check if rol_id is valid
                        if pulp.value(assign[(k_instance, tarea_name_csv, rol_id_csv)]) == 1:
                            fila.append(roles[rol_id_csv])
                            asignado_en_tarea = True
                            break 
                if not asignado_en_tarea:
                    # This indicates an issue if a task wasn't assigned.
                    # Could happen if the problem is infeasible or if roles_permitidos_for_task is empty/wrong.
                    fila.append("ERROR_NO_ASIGNADO") 
            writer.writerow(fila)
    print(f"\n✔️ ¡Instancias generadas y guardadas en '{file_path}' correctamente!")

    # Opcional: Imprimir conteo de T1 para JVG e HYV
    val_count_T1_JVG = pulp.value(count_T1_JVG)
    print(f"Conteo de T1 para JVG (1): {val_count_T1_JVG}")
    # HYV (role 2) is the other person eligible for T1.
    # Total T1 assignments are 20.
    print(f"Conteo de T1 para HYV (2): {20 - val_count_T1_JVG}")

elif prob.status == pulp.LpStatusInfeasible:
    print("\n❌ El problema es infactible. No se encontró solución que cumpla todas las restricciones.")
    print("Verifique las restricciones, especialmente R3 y R4, y la consistencia de 'tareas'.")
elif prob.status == pulp.LpStatusUnbounded:
    print("\n❌ El problema es no acotado. Esto suele indicar un error en la formulación del objetivo o restricciones faltantes.")
else:
    print(f"\n❓ Estado del solver: {pulp.LpStatus[prob.status]}")
