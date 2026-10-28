"""Prueba de humo opcional en entorno con pantalla: no altera la base real."""
import tempfile,time
from pathlib import Path
from saulo_sistema_experto import Aplicacion
with tempfile.TemporaryDirectory() as d:
    app=Aplicacion(Path(d)/'prueba.json')
    app.withdraw()
    app.entrada.insert('1.0', 'Solo si, estudio para el examen, apruebo\nestudio para el examen\napruebo si y solo si tengo el certificado')
    app.analizar()
    assert len(app.base.reglas)==3
    assert app.base.reglas[0]['formula']=='(q → p)', app.base.reglas[0]['formula']
    app.construir()
    tope=time.monotonic()+8
    while app.trabajando and time.monotonic()<tope:
        app.update()
        time.sleep(.03)
    assert not app.trabajando
    assert app.resultado is not None
    assert app.resultado['satisfacible']
    assert len(app.resultado['nodos'])>0
    print('Interfaz OK: reglas, árbol, ramas y modelos.')
    app.cerrar()
