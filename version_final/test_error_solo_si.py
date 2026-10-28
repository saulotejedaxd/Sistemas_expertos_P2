"""Regresión de la captura: SOLO SI al comienzo y modelos lógicos."""
import tempfile,unittest
from pathlib import Path
from saulo_sistema_experto import AnalizadorRecursivo,BaseDeConocimiento,formula,construir_tableau

class TestSoloSi(unittest.TestCase):
 def test_captura(self):
  self.assertEqual(formula(AnalizadorRecursivo('Solo si, estudio para el examen, apruebo').analizar()),'(apruebo → estudio para el examen)')
 def test_variantes(self):
  casos={
   'Solo si, A, B':'(B → A)',
   'Solo si A, B':'(B → A)',
   'B solo si A':'(B → A)',
   'Si A entonces B':'(A → B)',
   'Si y solo si, A, B':'(A ↔ B)',
   'Solo si, (A y C), B':'(B → (A ∧ C))',
   'A si y solo si B':'(A ↔ B)',
   'No A o B':'(¬A ∨ B)'
  }
  for texto,esperado in casos.items():
   with self.subTest(texto=texto):self.assertEqual(formula(AnalizadorRecursivo(texto).analizar()),esperado)
 def test_persistencia_y_reutilizacion(self):
  with tempfile.TemporaryDirectory() as carpeta:
   b=BaseDeConocimiento(Path(carpeta)/'reglas.json')
   reglas=b.agregar_lote('Solo si, estudio para el examen, apruebo\nApruebo solo si estudio para el examen')
   self.assertEqual(len(b.atomos),2)
   self.assertEqual(reglas[0]['formula'],reglas[1]['formula'])

if __name__=='__main__':unittest.main()
