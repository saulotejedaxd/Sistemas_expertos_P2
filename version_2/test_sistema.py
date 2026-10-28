import unittest,itertools,random,tempfile,json,time,threading
from pathlib import Path
from saulo_sistema_experto import *
def evaluar(n,m):
 if not n.hijos:return m[n.op]
 if n.op=='¬':return not evaluar(n.hijos[0],m)
 a,b=[evaluar(h,m) for h in n.hijos]
 return {'∧':a and b,'∨':a or b,'→':not a or b,'↔':a==b}[n.op]
class Pruebas(unittest.TestCase):
 def test_expansiones(self):
  for text in ['p ∧ q','p ∨ q','p → q','p ↔ q','¬(p ∨ q)','¬(p ∧ q)','¬(p → q)','¬(p ↔ q)','¬¬p']:
   n=AnalizadorRecursivo(text,True).analizar();result=construir_tableau([n]);keys=sorted(set(hojas(n)))
   for vals in itertools.product([False,True],repeat=len(keys)):
    m=dict(zip(keys,vals));self.assertEqual(evaluar(n,m),any(all(m[k]==v for k,v in r['valores'].items()) for r in result['modelos']),text)
 def test_cien_bases(self):
  rng=random.Random(2026)
  def crear(d):
   if not d or rng.random()<.3:return Nodo(rng.choice(['p','q','r']))
   op=rng.choice(['¬','∧','∨','→','↔']);return Nodo(op,(crear(d-1),) if op=='¬' else (crear(d-1),crear(d-1)))
  for _ in range(100):
   fs=[crear(3) for _ in range(3)];res=construir_tableau(fs)
   for vs in itertools.product([False,True],repeat=3):
    m=dict(zip(['p','q','r'],vs));self.assertEqual(all(evaluar(n,m) for n in fs),any(all(m[k]==v for k,v in r['valores'].items()) for r in res['modelos']))
 def test_espanol(self):
  with tempfile.TemporaryDirectory() as d:
   b=BaseDeConocimiento(Path(d)/'b.json');b.agregar_lote('Si es de día, entonces voy a trabajar\nes de día\nno voy a trabajar')
   self.assertEqual(len(b.atomos),2);self.assertFalse(construir_tableau([AnalizadorRecursivo(r['formula'],True).analizar() for r in b.reglas])['satisfacible'])
 def test_negacion_interna_y_sujeto(self):
  with tempfile.TemporaryDirectory() as d:
   b=BaseDeConocimiento(Path(d)/'b.json');b.agregar_lote('Si Juan estudia y entrega la tarea, entonces aprueba el examen\nJuan no estudia')
   self.assertEqual(list(b.atomos.values()),['Juan estudia','Juan entrega la tarea','Juan aprueba el examen']);self.assertEqual(b.reglas[-1]['formula'],'¬p')
 def test_migracion_transaccion(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'b.json';p.write_text(Path(__file__).with_name('base_conocimiento_saulo.json').read_text())
   b=BaseDeConocimiento(p);self.assertEqual(b.reglas[0]['formula'],'(¬p → q)');b.agregar('es de día');before=p.read_bytes()
   with self.assertRaises(ValueError):b.agregar_lote('llueve\nSi algo')
   self.assertEqual(before,p.read_bytes());self.assertEqual(BaseDeConocimiento(p).atomos,b.atomos)
 def test_sintaxis(self):
  for text in ['Si llueve','Si entonces llueve','llueve y','no','()','(llueve','llueve o o nieva','llueve entonces nieva']:
   with self.assertRaises(ValueError):AnalizadorRecursivo(text).analizar()
  n=AnalizadorRecursivo('Si es de día entonces (Si llueve entonces voy a trabajar)').analizar();self.assertEqual(n.hijos[1].op,'→')
 def test_letras_y_o(self):
  n=AnalizadorRecursivo('(y → ¬o)',True).analizar();self.assertEqual(formula(n),'(y → ¬o)')
 def test_limites(self):
  with self.assertRaises(AnalisisInterrumpido):construir_tableau([AnalizadorRecursivo('p ∨ q',True).analizar()],max_nodos=1)
  e=threading.Event();e.set()
  with self.assertRaises(AnalisisInterrumpido):construir_tableau([Nodo('p')],cancelar=e)
 def test_largo(self):
  with tempfile.TemporaryDirectory() as d:
   b=BaseDeConocimiento(Path(d)/'b.json');b.agregar_lote(Path(__file__).with_name('Prueba_larga.txt').read_text())
   fs=[AnalizadorRecursivo(r['formula'],True).analizar() for r in b.reglas];self.assertTrue(construir_tableau(fs)['satisfacible'])
   b.agregar('no el ciclo está autorizado');self.assertFalse(construir_tableau([AnalizadorRecursivo(r['formula'],True).analizar() for r in b.reglas])['satisfacible'])
if __name__=='__main__':unittest.main()
