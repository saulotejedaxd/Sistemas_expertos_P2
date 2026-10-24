"""Primera entrega: analizador simbólico de reglas en español.
Autor: Saulo Jaziel Tejeda Valle | Registro: 23310404.
Solo biblioteca estándar de Python; no usa IA.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ARCHIVO = Path(__file__).with_name("base_conocimiento_saulo.json")
OPERADOR = {"y": "∧", "o": "∨"}
SIN_SUJETO = {
    "si", "no", "es", "hay", "llueve", "nieva", "amanece", "anochece",
    "voy", "estoy", "soy", "tengo", "tenemos", "hoy", "mañana", "ayer",
    "cuando", "siempre", "entonces", "aprueba", "reprueba", "entrega",
    "estudia", "trabaja", "duerme", "enciende", "apaga", "puede", "debe",
    "el", "la", "los", "las", "un", "una", "mi", "su", "este", "esta",
}
INICIO_IMPERSONAL = ("es de día", "es de noche", "hay ", "llueve", "nieva")
SIN_PROPAGACION = {"es", "hay", "llueve", "nieva", "voy", "estoy", "soy", "hoy",
                   "mañana", "ayer", "el", "la", "los", "las", "un", "una",
                   "mi", "su", "este", "esta", "cuando"}
PATRON_OPERADORES = re.compile(r"\(|\)|\b(?:y|o)\b", re.IGNORECASE)
PATRON_CONDICIONAL = re.compile(r"^si\s+(.+?)\s*,?\s+entonces\s+(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class Nodo:
    tipo: str
    valor: str = ""
    izq: Nodo | None = None
    der: Nodo | None = None


def limpiar(frase: str) -> str:
    return " ".join(frase.strip(" \t\n\r,.;:¡!¿?").split())


def negacion(frase: str) -> tuple[bool, str]:
    """Detecta 'no Juan estudia' y 'Juan no estudia' como ¬(Juan estudia)."""
    frase = limpiar(frase)
    if frase.casefold().startswith("no "):
        base = limpiar(frase[3:])
        if not base:
            raise ValueError("Falta una afirmación después de 'no'.")
        return True, base
    separacion = re.search(r"\s+no\s+", frase, flags=re.IGNORECASE)
    if separacion:
        base = limpiar(frase[:separacion.start()] + " " + frase[separacion.end():])
        if not base:
            raise ValueError("Negación incompleta.")
        return True, base
    return False, frase


def sujeto_explicito(frase: str) -> str | None:
    """Heurística limitada: nombres propios con inicial mayúscula (Juan, Ana María)."""
    palabras = frase.split()
    if len(palabras) < 2 or palabras[0].casefold() in SIN_SUJETO:
        return None
    if not palabras[0][0].isupper() or not palabras[0][1:].islower():
        return None
    nombres = [palabras[0]]
    for palabra in palabras[1:3]:
        if len(palabra) > 1 and palabra[0].isupper() and palabra[1:].islower():
            nombres.append(palabra)
        else:
            break
    if len(nombres) >= len(palabras):
        return None
    return " ".join(nombres)


def enunciar(frase: str, sujeto: str | None) -> Nodo:
    es_negativo, base = negacion(frase)
    if not base:
        raise ValueError("Se encontró una afirmación vacía.")
    primero = base.split()[0].casefold()
    if (sujeto and not sujeto_explicito(base) and base[0].islower()
            and primero not in SIN_PROPAGACION and not base.casefold().startswith(INICIO_IMPERSONAL)):
        base = sujeto + " " + base
    afirmacion = Nodo("atomo", limpiar(base))
    return Nodo("neg", izq=afirmacion) if es_negativo else afirmacion


def separar_condicional(texto: str) -> tuple[str, str | None]:
    texto = limpiar(texto)
    if not texto:
        raise ValueError("Ingresa una oración.")
    if re.match(r"^si\s+", texto, flags=re.IGNORECASE):
        encontrado = PATRON_CONDICIONAL.match(texto)
        if not encontrado:
            raise ValueError("Usa la forma 'Si [condición], entonces [resultado]'.")
        return limpiar(encontrado.group(1)), limpiar(encontrado.group(2))
    return texto, None


class AnalizadorRecursivo:
    """Analizador descendente: ∧ tiene precedencia sobre ∨; permite paréntesis."""

    def __init__(self, expresion: str):
        self.simbolos: list[tuple[str, str]] = []
        inicio = 0
        for coincidencia in PATRON_OPERADORES.finditer(expresion):
            texto = limpiar(expresion[inicio:coincidencia.start()])
            if texto:
                self.simbolos.append(("ATOMO", texto))
            palabra = coincidencia.group().casefold()
            self.simbolos.append(({"y": "Y", "o": "O", "(": "(", ")": ")"}[palabra], palabra))
            inicio = coincidencia.end()
        texto = limpiar(expresion[inicio:])
        if texto:
            self.simbolos.append(("ATOMO", texto))
        self.pos = 0

    def siguiente(self) -> str:
        return self.simbolos[self.pos][0] if self.pos < len(self.simbolos) else "FIN"

    def consumir(self, esperado: str) -> str:
        if self.siguiente() != esperado:
            raise ValueError(f"Sintaxis inválida: se esperaba {esperado} y apareció {self.siguiente()}.")
        dato = self.simbolos[self.pos][1]
        self.pos += 1
        return dato

    def analizar(self) -> Nodo:
        arbol = self.disyuncion()
        if self.siguiente() != "FIN":
            raise ValueError(f"Operador o paréntesis inesperado: {self.siguiente()}.")
        return arbol

    def disyuncion(self) -> Nodo:
        arbol = self.conjuncion()
        while self.siguiente() == "O":
            self.consumir("O")
            arbol = Nodo("o", izq=arbol, der=self.conjuncion())
        return arbol

    def conjuncion(self) -> Nodo:
        arbol = self.termino()
        while self.siguiente() == "Y":
            self.consumir("Y")
            arbol = Nodo("y", izq=arbol, der=self.termino())
        return arbol

    def termino(self) -> Nodo:
        if self.siguiente() == "(":
            self.consumir("(")
            arbol = self.disyuncion()
            self.consumir(")")
            return arbol
        return Nodo("atomo", self.consumir("ATOMO"))


def recorrer(nodo: Nodo) -> list[str]:
    if nodo.tipo == "atomo":
        return [nodo.valor]
    return (recorrer(nodo.izq) if nodo.izq else []) + (recorrer(nodo.der) if nodo.der else [])


def añadir_sujeto(nodo: Nodo, sujeto: str | None) -> Nodo:
    if nodo.tipo == "atomo":
        return enunciar(nodo.valor, sujeto)
    return Nodo(nodo.tipo, izq=añadir_sujeto(nodo.izq, sujeto),
                der=añadir_sujeto(nodo.der, sujeto))


def serializar(nodo: Nodo, indices: dict[str, str], padre: int = 0) -> str:
    if nodo.tipo == "atomo":
        return indices[nodo.valor.casefold()]
    if nodo.tipo == "neg":
        interno = serializar(nodo.izq, indices, 4)
        if nodo.izq.tipo in {"y", "o"}:
            interno = f"({interno})"
        return f"¬{interno}"
    prioridad = {"o": 2, "y": 3}[nodo.tipo]
    izquierda = serializar(nodo.izq, indices, prioridad)
    derecha = serializar(nodo.der, indices, prioridad)
    expresion = f"{izquierda} {OPERADOR[nodo.tipo]} {derecha}"
    return f"({expresion})" if prioridad < padre else expresion


class BaseDeConocimiento:
    def __init__(self, ruta: Path = ARCHIVO):
        self.ruta = Path(ruta)
        self.atomos: dict[str, str] = {}
        self.reglas: list[dict[str, str]] = []
        if self.ruta.exists():
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            self.atomos = dict(datos["atomos"])
            self.reglas = list(datos["reglas"])

    def agregar(self, texto: str) -> dict[str, str]:
        izquierda, derecha = separar_condicional(texto)
        arbol_izq = AnalizadorRecursivo(izquierda).analizar()
        arbol_der = AnalizadorRecursivo(derecha).analizar() if derecha else None
        # Sólo se reconstruyen sujetos cuando existe un único nombre explícito.
        nombres = {nombre.casefold(): nombre for frase in recorrer(arbol_izq)
                   if (nombre := sujeto_explicito(negacion(frase)[1]))}
        sujeto = next(iter(nombres.values())) if len(nombres) == 1 else None
        arbol_izq = añadir_sujeto(arbol_izq, sujeto)
        if arbol_der:
            arbol_der = añadir_sujeto(arbol_der, sujeto)
        nuevas = dict(self.atomos)
        indices = {nombre.casefold(): identificador for identificador, nombre in nuevas.items()}
        for arbol in (arbol_izq, arbol_der):
            if arbol is None:
                continue
            for frase in recorrer(arbol):
                clave = frase.casefold()
                if clave not in indices:
                    identificador = f"X{len(nuevas) + 1}"
                    nuevas[identificador] = frase
                    indices[clave] = identificador
        formula = serializar(arbol_izq, indices)
        if arbol_der:
            # Los paréntesis hacen explícita la condición compuesta.
            if arbol_izq.tipo in {"y", "o"}:
                formula = f"({formula})"
            consecuente = serializar(arbol_der, indices)
            if arbol_der.tipo in {"y", "o"}:
                consecuente = f"({consecuente})"
            formula += " → " + consecuente
        regla = {"id": f"R{len(self.reglas) + 1}", "texto": limpiar(texto), "formula": formula}
        self.atomos = nuevas
        self.reglas.append(regla)
        self.guardar()
        return regla

    def guardar(self) -> None:
        self.ruta.write_text(json.dumps({"atomos": self.atomos, "reglas": self.reglas},
                                        ensure_ascii=False, indent=2), encoding="utf-8")

    def mostrar(self) -> str:
        a = "\n".join(f"  {clave} = {valor}" for clave, valor in self.atomos.items()) or "  (vacío)"
        r = "\n".join(f"  {dato['id']} = {dato['formula']}" for dato in self.reglas) or "  (vacío)"
        return f"ÁTOMOS\n{a}\n\nREGLAS\n{r}"


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Analizador de reglas sin IA")
    parser.add_argument("--demo", action="store_true", help="Ejecuta un ejemplo reproducible")
    args = parser.parse_args()
    base = BaseDeConocimiento()
    if args.demo:
        for ejemplo in ["Si Juan estudia y entrega la tarea, entonces aprueba el examen",
                        "Si Juan aprueba el examen, entonces obtiene su certificado"]:
            print("Entrada:", ejemplo)
            print("Salida:", base.agregar(ejemplo)["formula"], "\n")
        print(base.mostrar())
        return
    print("SISTEMAS EXPERTOS | Saulo Jaziel Tejeda Valle | 23310404")
    print("Escribe una regla por línea. Comandos: :ver, :salir")
    while True:
        try:
            texto = input("\nRegla > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nFin.")
            return
        if texto.casefold() in {":salir", "salir", ":q"}:
            return
        if texto.casefold() == ":ver":
            print("\n" + base.mostrar())
            continue
        if not texto:
            continue
        try:
            regla = base.agregar(texto)
            print(f"\n✓ {regla['id']} = {regla['formula']}")
            print(base.mostrar())
        except (ValueError, OSError, json.JSONDecodeError) as error:
            print(f"No se guardó la regla: {error}")


if __name__ == "__main__":
    main()
