import pulp
import csv

# -------- DATOS --------
ROLES_PERSONAS = {
    "DG": ["JVG"],
    "DR": ["HYV"],
    "DM": ["PGR"],
    "DE": ["MFE"],
    "TR": ["GTR", "LPG", "RGB", "HYV", "BJC"],
    "TC": ["RGB", "MDS", "LPG"],
    "PS": ["HJR", "PTS", "IHP"]
}

TAREAS_ROLES = {
    "T1": ["DR"],
    "T2.1": ["TR"],
    "T2.2": ["TC"],
    "T3": ["DM"],
    "T4": ["DE", "PS"]
}

def get_valid_personas(tarea):
    personas = set()
    for rol in TAREAS_ROLES[tarea]:
        personas.update(ROLES_PERSONAS.get(rol, []))
    return list(personas)

def resolver_instancia(exclusiones):
    model = pulp.LpProblem("Asignacion_Tareas_BPMS", pulp.LpMinimize)

    personas = set([p for lista in ROLES_PERSONAS.values() for p in lista])
    tareas = list(TAREAS_ROLES.keys())
    variables = pulp.LpVariable.dicts("Asignado", (personas, tareas), cat="Binary")

    model += 0, "Dummy Objective"

    for tarea in tareas:
        validos = get_valid_personas(tarea)
        model += pulp.lpSum([variables[persona][tarea] for persona in validos]) == 1, f"Asignacion_unica_{tarea}"

    for persona in personas:
        model += variables[persona]["T2.1"] + variables[persona]["T2.2"] <= 1, f"SoD_T2_1_T2_2_{persona}"
        model += variables[persona]["T3"] + variables[persona]["T4"] <= 1, f"SoD_T3_T4_{persona}"

    if "JVG" in personas:
        model += variables["JVG"]["T2.1"] == 0
        model += variables["JVG"]["T2.2"] == 0
        model += variables["JVG"]["T3"] == 0
        model += variables["JVG"]["T4"] == 0

    # Prohibir repeticiones exactas
    for excl in exclusiones:
        persona = excl['persona']
        tarea = excl['tarea']
        model += variables[persona][tarea] == 0

    solver = pulp.PULP_CBC_CMD(msg=0)
    model.solve(solver)

    asignaciones = {}
    for tarea in tareas:
        for persona in personas:
            if pulp.value(variables[persona][tarea]) == 1:
                asignaciones[tarea] = persona

    return asignaciones, pulp.LpStatus[model.status]

# -------- MAIN --------
if __name__ == "__main__":
    instancias = []
    NUM_INSTANCIAS = 20
    exclusiones = []

    for i in range(NUM_INSTANCIAS):
        asignacion, status = resolver_instancia(exclusiones)
        if status != "Optimal":
            print(f"Error al generar instancia {i+1}")
        else:
            instancias.append(asignacion)
            for tarea, persona in asignacion.items():
                exclusiones.append({'persona': persona, 'tarea': tarea})

    with open("sod_verification/instancias_bpmn.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Instancia", "T1", "T2.1", "T2.2", "T3", "T4"])

        for idx, instancia in enumerate(instancias, start=1):
            writer.writerow([
                idx,
                instancia.get("T1", ""),
                instancia.get("T2.1", ""),
                instancia.get("T2.2", ""),
                instancia.get("T3", ""),
                instancia.get("T4", "")
            ])

    print("\n✔️ ¡Instancias generadas y guardadas en 'instancias_bpmn.csv' correctamente!")
