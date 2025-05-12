import csv
from collections import Counter

def cargar_instancias(csv_file):
    instancias = []
    with open(csv_file, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            instancias.append(row)
    return instancias

def validar_instancias(instancias):
    errores = []
    participaciones = Counter()

    for idx, instancia in enumerate(instancias, start=1):
        t1 = instancia["T1"]
        t21 = instancia["T2.1"]
        t22 = instancia["T2.2"]
        t3 = instancia["T3"]
        t4 = instancia["T4"]

        # R1 Separación T2.1 y T2.2
        if t21 == t22:
            errores.append(f"Error R1 en instancia {idx}: T2.1 ({t21}) y T2.2 ({t22}) son iguales")

        # R2 Separación T3 y T4
        if t3 == t4:
            errores.append(f"Error R2 en instancia {idx}: T3 ({t3}) y T4 ({t4}) son iguales")

        # R3 Binding GTR-MDS
        if t21 == "GTR" and t22 != "MDS":
            errores.append(f"Error R3 en instancia {idx}: Si T2.1 es GTR, T2.2 debería ser MDS (es {t22})")

        # R4 JVG sólo en T1
        if "JVG" in [t21, t22, t3, t4]:
            errores.append(f"Error R4 en instancia {idx}: JVG participa fuera de T1")

        # Contar participaciones
        for user in [t1, t21, t22, t3, t4]:
            participaciones[user] += 1

    # R5 Fairness (básico, opcional)
    promedio = sum(participaciones.values()) / len(participaciones)
    for user, count in participaciones.items():
        if abs(count - promedio) > 3:  # permitimos una variación razonable
            errores.append(f"Advertencia R5: {user} tiene participación desequilibrada ({count} tareas)")

    return errores

if __name__ == "__main__":
    RUTA_FICHERO = "sod_verification/new_instancias_bpmn.csv"
    instancias = cargar_instancias(RUTA_FICHERO)
    errores = validar_instancias(instancias)

    if not errores:
        print("\n✔️ ¡Todas las instancias son válidas según las restricciones!")
    else:
        print("\n❌ Errores encontrados:")
        for err in errores:
            print("-", err)
