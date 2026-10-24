# Sistemas expertos — Saulo

**Saulo Jaziel Tejeda Valle · Registro 23310404**

## Versiones

| Carpeta | Contenido |
| --- | --- |
| [version_1](version_1/) | Copia exacta de los archivos que estaban en el repositorio antes de esta actualización. |
| [version_final](version_final/) | Interfaz gráfica en Python con análisis recursivo, árbol semántico y modelos. |

La versión 1 conserva el árbol de archivos del commit `009b21ed4b375784063c039ff00d26773f05a45e` sin modificar su contenido. El historial anterior sigue disponible.

## Ejecutar la versión final

1. Descarga o clona el repositorio y extrae los archivos si usas un ZIP.
2. Entra a **version_final**.
3. Abre **Iniciar_Saulo.bat** en Windows con Python 3.10 o posterior y Tkinter instalado.

También puedes ejecutar `python version_final/saulo_sistema_experto.py`.

Pega una regla o hecho por línea en **ENTRADA EN ESPAÑOL**, pulsa **Analizar y guardar** y después **Construir árbol**. La base incluye la regla previa de Saulo; exporta y reinicia la base si deseas probar exclusivamente un ejemplo nuevo.

## Funciones de la versión final

- Cinco conectivos: ∧, ∨, ¬, → y ↔; átomos p, q, r… y fórmulas por regla.
- Análisis descendente y expansión recursiva de tableaux.
- Árbol con fórmulas aplicadas, contradicciones, ramas abiertas y cerradas.
- Zoom, arrastre y ajuste del árbol completo a la ventana.
- Modelos parciales de las ramas abiertas y declaración de insatisfacibilidad cuando todas se cierran.
- Guardado de la base, exportación JSON, cancelación y límites explícitos de análisis.
- Panel de entrada con ancho mínimo para evitar que se colapse al iniciar.

Las frases deben utilizar los conectivos admitidos; no se unifican sinónimos. Revisa [LEEME.txt](version_final/LEEME.txt) para sintaxis, límites y uso.

## Validación

```bash
python -m unittest discover -s version_final -v
```

Nueve pruebas: expansiones, 100 bases comparadas con tablas de verdad, texto largo, contradicciones, negación, sintaxis, migración y límites. La ventana y el zoom también se comprobaron en pantalla virtual durante el desarrollo.
