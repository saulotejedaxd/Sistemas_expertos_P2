"""Pruebas de español controlado y preservación de lógica proposicional."""
import itertools
import json
import tempfile
import unittest
from pathlib import Path
from saulo_sistema_experto import AnalizadorRecursivo, BaseDeConocimiento, construir_tableau, formula, hojas


class PruebasConectores(unittest.TestCase):
    def test_aliases(self):
        casos = {
            'A y B': '(A ∧ B)',
            'A además B': '(A ∧ B)',
            'A así como B': '(A ∧ B)',
            'A pero B': '(A ∧ B)',
            'A aunque B': '(A ∧ B)',
            'A e B': '(A ∧ B)',
            'A o B': '(A ∨ B)',
            'A o bien B': '(A ∨ B)',
            'A u B': '(A ∨ B)',
            'A a menos que B': '(A ∨ B)',
            'A salvo que B': '(A ∨ B)',
            'no A': '¬A',
            'tampoco A': '¬A',
            'es falso que A': '¬A',
            'no es verdad que A': '¬A',
            'no es cierto que A': '¬A',
            'ni A ni B': '(¬A ∧ ¬B)',
            'A implica B': '(A → B)',
            'A implica que B': '(A → B)',
            'A por lo tanto B': '(A → B)',
            'A si B': '(B → A)',
            'A solo si B': '(A → B)',
            'A solamente si B': '(A → B)',
            'A únicamente si B': '(A → B)',
            'Si A entonces B': '(A → B)',
            'Si A, entonces B': '(A → B)',
            'Si A, B': '(A → B)',
            'Cuando A, B': '(A → B)',
            'Siempre que A, B': '(A → B)',
            'En caso de que A, B': '(A → B)',
            'A si y solo si B': '(A ↔ B)',
            'A si y solamente si B': '(A ↔ B)',
            'A equivale a B': '(A ↔ B)',
            'A es equivalente a B': '(A ↔ B)',
            '¬(A ∧ B)': '¬(A ∧ B)',
            '(A ∧ B) → C': '((A ∧ B) → C)',
        }
        for frase,esperado in casos.items():
            with self.subTest(frase=frase):
                self.assertEqual(formula(AnalizadorRecursivo(frase).analizar()),esperado)

    def test_formas_espanol_reales(self):
        casos = {
            'Si Juan estudia y entrega la tarea, entonces aprueba el examen':
              '(Juan estudia ∧ entrega la tarea)',
            'Cuando llueve, llevo paraguas': '(llueve → llevo paraguas)',
            'No llueve y tampoco hace frío': '(¬llueve ∧ ¬hace frío)',
            'Juan no estudia ni trabaja': '(¬Juan estudia ∧ ¬trabaja)',
            '"Juan y María estudian" o aprueban': '(Juan y María estudian ∨ aprueban)',
            'Si (llueve o nieva), entonces no salgo': '((llueve ∨ nieva) → ¬salgo)',
            'A si B': '(B → A)',
            'A solo si B': '(A → B)',
        }
        for frase,esperado in casos.items():
            salida=formula(AnalizadorRecursivo(frase).analizar())
            with self.subTest(frase=frase):
                self.assertIn(esperado,salida)

    def test_atomizacion_y_contradiccion(self):
        with tempfile.TemporaryDirectory() as d:
            b=BaseDeConocimiento(Path(d)/'b.json')
            b.agregar_lote('Si Juan estudia y entrega la tarea, entonces aprueba el examen\nJuan no estudia\nJuan estudia')
            self.assertEqual(list(b.atomos.values()),['Juan estudia','Juan entrega la tarea','Juan aprueba el examen'])
            self.assertEqual(b.reglas[1]['formula'],'¬p')
            self.assertFalse(construir_tableau([AnalizadorRecursivo(r['formula'],True).analizar() for r in b.reglas])['satisfacible'])

    def test_condicional_reverse_y_positivo(self):
        with tempfile.TemporaryDirectory() as d:
            b=BaseDeConocimiento(Path(d)/'b.json')
            b.agregar_lote('Trabajo si estudio\nEstudio\nNo trabajo')
            self.assertFalse(construir_tableau([AnalizadorRecursivo(r['formula'],True).analizar() for r in b.reglas])['satisfacible'])

    def test_bicondicional_negacion(self):
        with tempfile.TemporaryDirectory() as d:
            b=BaseDeConocimiento(Path(d)/'b.json')
            b.agregar_lote('llueve si y solo si hace frío\nllueve\nno hace frío')
            self.assertFalse(construir_tableau([AnalizadorRecursivo(r['formula'],True).analizar() for r in b.reglas])['satisfacible'])

    def test_archivo_original_permanece(self):
        original=Path(__file__).with_name('base_conocimiento_saulo.json').read_bytes()
        data=json.loads(original)
        self.assertIn('atomos',data)
        self.assertIn('reglas',data)
        self.assertGreater(len(data['reglas']),0)
        self.assertEqual(original,Path(__file__).with_name('base_conocimiento_saulo.json').read_bytes())

    def test_sintaxis_rechazada_sin_guardar(self):
        with tempfile.TemporaryDirectory() as d:
            b=BaseDeConocimiento(Path(d)/'b.json')
            b.agregar('llueve')
            previo=b.ruta.read_bytes()
            for invalida in ('llueve y','si llueve','si llueve entonces','no','llueve o o nieva','(llueve','llueve entonces nieva'):
                with self.subTest(invalida=invalida):
                    with self.assertRaises(ValueError):b.agregar_lote('hace frío\n'+invalida)
                    self.assertEqual(b.ruta.read_bytes(),previo)


if __name__=='__main__':unittest.main()
