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

# Tareas y roles permitidos
tareas = {
    "T1": [2],              # HYV (DR)
    "T2.1": [3, 4, 5, 6, 2],# TR (GTR, LPG, RGB, BJC, HYV)
    "T2.2": [5, 7, 4],      # TC (RGB, MDS, LPG)
    "T3": [8],              # PGR (DM)
    "T4": [9, 10, 11, 12]   # DE y PS (MFE, HJR, PTS, IHP)
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
    for tarea, roles_permitidos in tareas.items():
        prob += pulp.lpSum(assign[(k, tarea, rol)] for rol in roles_permitidos) == 1

# Cada persona como mucho realiza una tarea por instancia
for k in range(20):
    for rol in roles:
        prob += pulp.lpSum(assign[(k, tarea, rol)] for tarea in tareas) <= 1

# R1: Separación de deberes entre T2.1 y T2.2
for k in range(20):
    for rol in roles:
        prob += assign[(k, "T2.1", rol)] + assign[(k, "T2.2", rol)] <= 1

# R2: Separación de deberes entre T3 y T4
for k in range(20):
    for rol in roles:
        prob += assign[(k, "T3", rol)] + assign[(k, "T4", rol)] <= 1

# R3: Binding - Si GTR realiza T2.1, MDS realiza T2.2
for k in range(20):
    prob += assign[(k, "T2.1", 3)] - assign[(k, "T2.2", 7)] == 0

# R4: JVG sólo puede participar en T1
for k in range(20):
    for tarea in ["T2.1", "T2.2", "T3", "T4"]:
        prob += assign[(k, tarea, 1)] == 0

# --------- OBJETIVO (Dummy) ---------
prob += 0

# --------- SOLVER ---------
solver = pulp.PULP_CBC_CMD(msg=1)
prob.solve(solver)

# --------- EXPORTAR A CSV ---------
output_dir = "sod_verification"
os.makedirs(output_dir, exist_ok=True)

with open(os.path.join(output_dir, "new_instancias_bpmn.csv"), mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Instancia", "T1", "T2.1", "T2.2", "T3", "T4"])

    for k in range(20):
        fila = [k]
        for tarea in ["T1", "T2.1", "T2.2", "T3", "T4"]:
            encontrado = False
            for rol in roles:
                if pulp.value(assign[(k, tarea, rol)]) == 1:
                    fila.append(roles[rol])
                    encontrado = True
                    break
            if not encontrado:
                raise Exception(f"❌ Error: No asignado en instancia {k}, tarea {tarea}")
        writer.writerow(fila)

print("\n✔️ ¡Instancias generadas y guardadas en 'sod_verification/new_instancias_bpmn.csv' correctamente!")
