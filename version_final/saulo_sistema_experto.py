"""Sistema experto gráfico de Saulo Jaziel Tejeda Valle, 23310404.
Python estándar: análisis descendente recursivo y tableaux proposicionales.
"""
from __future__ import annotations
import json, re, os, time, threading, queue
from pathlib import Path
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
ARCHIVO=Path(__file__).with_name('base_conocimiento_saulo.json')

@dataclass(frozen=True)
class Nodo:
    op: str
    hijos: tuple=()

def negar(n): return Nodo('¬',(n,))
def formula(n):
    if not n.hijos:return n.op
    if n.op=='¬':return '¬'+formula(n.hijos[0])
    return '('+formula(n.hijos[0])+' '+n.op+' '+formula(n.hijos[1])+')'
def letra(i):
    abc='pqrstuvwxyzabcdefghijklmno'
    return abc[i%26]+(str(i//26+1) if i>=26 else '')
def clave(s):return ' '.join(s.casefold().split())

class AnalizadorRecursivo:
    """Analizador descendente para español controlado, sin IA.

    Precedencia, de mayor a menor: ¬, ∧, ∨, →, ↔. Los condicionales
    escritos al inicio usan «si A, entonces B» o «si A, B».
    Las comillas dobles preservan proposiciones con conectores literales.
    """
    ALIASES = (
        ('si y solo si', '↔'), ('si, y solo si', '↔'),
        ('si y solamente si', '↔'), ('si y únicamente si', '↔'),
        ('es equivalente a', '↔'), ('equivale a', '↔'),
        ('siempre y cuando', 'COND'), ('en caso de que', 'COND'),
        ('siempre que', 'COND'), ('cuando', 'COND'),
        ('a menos que', '∨'), ('salvo que', '∨'),
        ('únicamente si', 'SOLO_SI'), ('solamente si', 'SOLO_SI'),
        ('solo si', 'SOLO_SI'), ('sólo si', 'SOLO_SI'),
        ('por lo tanto', '→'), ('por tanto', '→'),
        ('implica que', '→'), ('implica', '→'),
        ('es falso que', '¬'), ('no es cierto que', '¬'),
        ('no es verdad que', '¬'), ('es mentira que', '¬'),
        ('y además', '∧'), ('así como', '∧'),
        ('además', '∧'), ('pero', '∧'), ('también', '∧'),
        ('asimismo', '∧'), ('aunque', '∧'), ('ni', 'NI'),
        ('o bien', '∨'), ('o', '∨'), ('u', '∨'), ('y', '∧'), ('e', '∧'),
        ('tampoco', '¬'), ('entonces', 'ENTONCES'),
        ('si', 'SI'), ('no', '¬'),
    )
    _alternativas = sorted(ALIASES, key=lambda p: len(p[0]), reverse=True)
    _patron_es = re.compile(
        r'"(?:\\.|[^"\\])*"|[()¬∧∨→↔]|,|(?<!\w)(?:' +
        '|'.join(re.escape(k).replace(r'\ ', r'\s+') for k, _ in _alternativas) +
        r')(?!\w)', re.IGNORECASE)
    _patron_sim = re.compile(r'[()¬∧∨→↔]')
    _op = {'∧','∨','→','↔','¬','SI','COND','SOLO_SI','ENTONCES','NI','(',')',','}

    def __init__(self, texto, simbolica=False):
        if len(texto)>15000:
            raise ValueError('La regla es demasiado larga; divídela en reglas menores.')
        self.simbolica = simbolica
        self.tokens = []
        patron = self._patron_sim if simbolica else self._patron_es
        pos = 0
        for m in patron.finditer(texto):
            self._agregar_atomo(texto[pos:m.start()])
            raw = m.group()
            if not simbolica and raw.startswith('"'):
                # Una proposición entre comillas no se separa aunque contenga «y», «o», etc.
                self.tokens.append(('ATOMO', raw[1:-1].replace(r'\"', '"')))
            elif raw == ',':
                self.tokens.append((',', ','))
            elif raw in '()¬∧∨→↔':
                self.tokens.append((raw, raw))
            else:
                token = raw if simbolica else next(
                    v for k,v in self._alternativas if re.fullmatch(k.replace(' ', r'\s+'), raw, re.I)
                )
                self.tokens.append((token,raw))
            pos=m.end()
        self._agregar_atomo(texto[pos:])
        # Comas de estilo antes de «entonces», «y», etc., no significan implicación.
        self.pos=0

    def _agregar_atomo(self, texto):
        texto=' '.join(texto.strip(' \t\n\r.;:¡!¿?').split())
        if texto:
            self.tokens.append(('ATOMO',texto))

    def actual(self):
        return self.tokens[self.pos][0] if self.pos<len(self.tokens) else None

    def tomar(self, esperado=None):
        t=self.actual()
        if t is None or (esperado is not None and t!=esperado):
            raise ValueError(f"Se esperaba {esperado or 'una proposición'}; apareció {t or 'fin de la regla'}.")
        self.pos+=1
        return self.tokens[self.pos-1][1]

    def _comas_estilo(self):
        # La coma antes del conector explícito «entonces» o «y» es puntuación.
        while self.actual()==',' and self.pos+1<len(self.tokens) and self.tokens[self.pos+1][0] in {'ENTONCES','∧','∨','→','↔'}:
            self.tomar(',')

    def _expresion_desde_tokens(self, tokens):
        """Analiza una subexpresión conservando los tokens originales y sus comillas."""
        if not tokens:
            raise ValueError('Falta una proposición en la regla.')
        otro=self.__class__.__new__(self.__class__)
        otro.tokens=list(tokens)
        otro.pos=0
        otro.simbolica=self.simbolica
        return otro.analizar()

    def _conector_inicial(self):
        """Soporta «Solo si, A, B»: B → A y «Si y solo si, A, B»: A ↔ B.

        La coma anterior a A es opcional; la coma entre A y B es obligatoria.
        Solo se separa en comas fuera de paréntesis.
        """
        tipo=self.tokens[0][0]
        inicio=1
        if inicio < len(self.tokens) and self.tokens[inicio][0]==',':
            inicio+=1
        profundidad=0
        separador=None
        for indice in range(inicio,len(self.tokens)):
            token=self.tokens[indice][0]
            if token=='(':
                profundidad+=1
            elif token==')':
                profundidad-=1
                if profundidad<0:raise ValueError('Paréntesis de cierre sin apertura.')
            elif token==',' and profundidad==0:
                if separador is not None:
                    raise ValueError('El conector inicial requiere dos proposiciones, separadas por una coma.')
                separador=indice
        if profundidad!=0:raise ValueError('Paréntesis sin cerrar.')
        if separador is None:
            raise ValueError('Escribe «Solo si, condición, consecuencia» o «consecuencia solo si condición».')
        condicion=self._expresion_desde_tokens(self.tokens[inicio:separador])
        consecuencia=self._expresion_desde_tokens(self.tokens[separador+1:])
        if tipo=='SOLO_SI':
            return Nodo('→',(consecuencia,condicion))
        return Nodo('↔',(condicion,consecuencia))

    def analizar(self):
        try:
            if not self.simbolica and self.tokens and self.tokens[0][0] in {'SOLO_SI','↔'}:
                return self._conector_inicial()
            resultado=self.equivalencia()
            self._comas_estilo()
        except RecursionError:
            raise ValueError('Demasiados paréntesis o negaciones anidados.') from None
        if self.actual() is not None:
            raise ValueError(f'Conector sin completar o texto inesperado: {self.actual()}.')
        return resultado

    def equivalencia(self):
        a=self.implicacion()
        while True:
            self._comas_estilo()
            if self.actual()!='↔': break
            self.tomar('↔')
            a=Nodo('↔',(a,self.implicacion()))
        return a

    def implicacion(self):
        a=self.disyuncion()
        self._comas_estilo()
        t=self.actual()
        if t in {'→','SOLO_SI','SI','COND'}:
            self.tomar()
            b=self.implicacion()  # Asociatividad derecha.
            if t in {'SI','COND'}:
                return Nodo('→',(b,a))  # «A si B» significa B → A.
            return Nodo('→',(a,b))
        return a

    def disyuncion(self):
        a=self.conjuncion()
        while True:
            self._comas_estilo()
            if self.actual()!='∨':break
            self.tomar('∨')
            a=Nodo('∨',(a,self.conjuncion()))
        return a

    def conjuncion(self):
        a=self.termino()
        while True:
            self._comas_estilo()
            if self.actual() not in {'∧','NI'}:break
            t=self.actual();self.tomar()
            b=self.termino()
            a=Nodo('∧',(a,negar(b) if t=='NI' else b))
        return a

    def termino(self):
        t=self.actual()
        if t is None:
            raise ValueError('Falta una proposición al final de la regla.')
        if t in {'¬','NI'}:
            self.tomar()
            return negar(self.termino())
        if t in {'SI','COND'}:
            self.tomar()
            antecedente=self.equivalencia()
            # Antecedente termina ante «entonces» o la coma separadora.
            if self.actual()=='ENTONCES':
                self.tomar('ENTONCES')
            elif self.actual()==',':
                self.tomar(',')
                if self.actual()=='ENTONCES':self.tomar('ENTONCES')
            else:
                raise ValueError('En «si/cuando ...» separa condición y resultado con «entonces» o una coma.')
            consecuencia=self.equivalencia()
            return Nodo('→',(antecedente,consecuencia))
        if t=='(':
            self.tomar('(')
            a=self.equivalencia()
            self.tomar(')')
            return a
        if t!='ATOMO':
            raise ValueError('Conector sin proposición: '+str(t))
        nombre=self.tomar('ATOMO')
        if self.simbolica:
            if not re.fullmatch(r'[a-z]\d*|X\d+',nombre):
                raise ValueError('Identificador simbólico inválido: '+nombre)
            return Nodo(nombre)
        # «Juan no estudia» equivale a ¬(Juan estudia).
        if self.actual()=='¬':
            self.tomar('¬')
            if self.actual()!='ATOMO':
                raise ValueError('Después de una negación interna falta una acción.')
            accion=self.tomar('ATOMO')
            return negar(Nodo(' '.join((nombre+' '+accion).split())))
        return Nodo(nombre)

def hojas(n):
    if not n.hijos:return [n.op]
    return [s for h in n.hijos for s in hojas(h)]
def transformar(n,f):
    return Nodo(f(n.op)) if not n.hijos else Nodo(n.op,tuple(transformar(h,f) for h in n.hijos))
SIN_SUJETO={'si','no','es','hay','llueve','nieva','amanece','anochece','voy','estoy','soy','tengo','tenemos','hoy','mañana','ayer','cuando','siempre','entonces','aprueba','reprueba','entrega','estudia','trabaja','duerme','enciende','apaga','puede','debe','el','la','los','las','un','una','mi','su','este','esta'}
SIN_PROPAGACION={'es','hay','llueve','nieva','voy','estoy','soy','tengo','tenemos','hoy','mañana','ayer','el','la','los','las','un','una','mi','su','este','esta','cuando'}
def sujeto(s):
    ps=s.split()
    if len(ps)<2 or ps[0].casefold() in SIN_SUJETO or not ps[0].istitle():return None
    ns=[ps[0]]
    for p in ps[1:3]:
        if len(p)>1 and p.istitle():ns.append(p)
        else:break
    return ' '.join(ns) if len(ns)<len(ps) else None

class BaseDeConocimiento:
    def __init__(self,ruta=ARCHIVO):
        self.ruta=Path(ruta);self.atomos={};self.reglas=[]
        if self.ruta.exists():
            datos=json.loads(self.ruta.read_text(encoding='utf-8-sig'))
            if not isinstance(datos.get('atomos'),dict) or not isinstance(datos.get('reglas'),list):raise ValueError('Formato de base inválido.')
            cambios={k:letra(i) for i,k in enumerate(datos['atomos'])}
            self.atomos={cambios[k]:v for k,v in datos['atomos'].items()}
            for r in datos['reglas']:
                n=AnalizadorRecursivo(r['formula'],True).analizar()
                n=transformar(n,lambda a:cambios[a])
                self.reglas.append({'id':r['id'],'texto':r.get('texto',r.get('original','')),'formula':formula(n)})
    def guardar(self):
        contenido=json.dumps({'atomos':self.atomos,'reglas':self.reglas},ensure_ascii=False,indent=2)
        if self.ruta.exists() and not self.ruta.with_suffix('.json.bak').exists():
            self.ruta.with_suffix('.json.bak').write_bytes(self.ruta.read_bytes())
        temp=self.ruta.with_suffix('.tmp');temp.write_text(contenido,encoding='utf-8');os.replace(temp,self.ruta)
    def agregar_lote(self,texto):
        lines=[l.strip() for l in texto.splitlines() if l.strip()]
        if not lines:raise ValueError('Escribe por lo menos una regla o hecho.')
        atoms=self.atomos.copy();catalogo={clave(v):k for k,v in atoms.items()};nuevas=[]
        for numero,linea in enumerate(lines,1):
            try:
                analizador=AnalizadorRecursivo(linea)
                n=analizador.analizar()
                nombres={sujeto(s) for s in hojas(n) if sujeto(s)}
                persona=next(iter(nombres)) if len(nombres)==1 else None
                def registrar(s):
                    if persona and s[0].islower() and not sujeto(s) and s.split()[0].casefold() not in SIN_PROPAGACION:s=persona+' '+s
                    k=clave(s)
                    if k not in catalogo:
                        i=len(atoms)
                        while letra(i) in atoms:i+=1
                        catalogo[k]=letra(i);atoms[letra(i)]=s
                    return catalogo[k]
                # Asigna letras según la primera aparición en el TEXTO, no
                # según el orden de los operandos del árbol (que se invierte
                # para la construcción «Solo si, B, A» y «A si B»).
                tokens=analizador.tokens
                indice=0
                while indice<len(tokens):
                    if tokens[indice][0]=='ATOMO':
                        frase=tokens[indice][1]
                        if (indice+2<len(tokens) and tokens[indice+1][0]=='¬'
                                and tokens[indice+2][0]=='ATOMO'):
                            frase+=' '+tokens[indice+2][1]
                            indice+=2
                        registrar(frase)
                    indice+=1
                n=transformar(n,registrar)
                nuevas.append({'id':f'R{len(self.reglas)+len(nuevas)+1}','texto':linea,'formula':formula(n)})
            except (ValueError,RecursionError) as e:raise ValueError(f'Línea {numero}: {e}') from None
        prev=self.atomos,self.reglas;self.atomos=atoms;self.reglas=self.reglas+nuevas
        try:self.guardar()
        except OSError:self.atomos,self.reglas=prev;raise
        return nuevas
    def agregar(self,texto):return self.agregar_lote(texto)[0]
    def mostrar(self):return 'ÁTOMOS\n'+'\n'.join(f'{a} = {s}' for a,s in self.atomos.items())+'\nREGLAS\n'+'\n'.join(f"{r['id']}: {r['formula']}" for r in self.reglas)

def expansion(n):
    if not n.hijos:return None
    if n.op=='¬':
        a=n.hijos[0]
        if not a.hijos:return None
        if a.op=='¬':return [[a.hijos[0]]]
        x,y=a.hijos
        return {'∧':[[negar(x)],[negar(y)]],'∨':[[negar(x),negar(y)]],'→':[[x,negar(y)]],'↔':[[x,negar(y)],[negar(x),y]]}[a.op]
    x,y=n.hijos
    return {'∧':[[x,y]],'∨':[[x],[y]],'→':[[negar(x)],[y]],'↔':[[x,y],[negar(x),negar(y)]]}[n.op]
class AnalisisInterrumpido(Exception):pass

def construir_tableau(formulas,cancelar=None,max_nodos=5000,segundos=10):
    """Tableau recursivo. Todas las fórmulas iniciales se suponen verdaderas.
    Guarda nodos planos para exportación y dibujo sin recursión adicional.
    """
    nodos=[];modelos=[];inicio=time.monotonic()
    def rama(fs,aplicadas,nuevas,padre):
        if cancelar and cancelar.is_set():raise AnalisisInterrumpido('Análisis cancelado; no se emitió una conclusión.')
        if len(nodos)>=max_nodos or time.monotonic()-inicio>segundos:raise AnalisisInterrumpido('Límite de recursos alcanzado. Análisis incompleto: reduce el número de alternativas.')
        valores={};conflicto=None
        for f in fs:
            if not f.hijos:a,v=f.op,True
            elif f.op=='¬' and not f.hijos[0].hijos:a,v=f.hijos[0].op,False
            else:continue
            if a in valores and valores[a]!=v:conflicto=a
            valores[a]=v
        idx=len(nodos)
        node={'id':idx,'padre':padre,'nuevas':[formula(f) for f in nuevas],'aplicada':None,'estado':'cerrada' if conflicto else 'abierta','contradiccion':conflicto,'hijos':[]}
        nodos.append(node)
        if conflicto:return idx
        pendientes=[(f,expansion(f)) for f in fs if f not in aplicadas and expansion(f) is not None]
        if not pendientes:
            modelos.append({'nodo':idx,'valores':valores});return idx
        conjunto=set(fs)
        def prioridad(par):
            opciones=par[1]
            descartes=sum(any(negar(f) in conjunto or f.op=='¬' and f.hijos[0] in conjunto for f in extra) for extra in opciones)
            return (len(opciones),-descartes)
        f,opciones=min(pendientes,key=prioridad);node['aplicada']=formula(f);node['estado']='expandida'
        for extra in opciones:
            child=rama(fs+[x for x in extra if x not in conjunto],aplicadas|{f},extra,idx)
            node['hijos'].append(child)
        return idx
    try:rama(list(dict.fromkeys(formulas)),set(),list(dict.fromkeys(formulas)),None)
    except RecursionError:raise AnalisisInterrumpido('Profundidad excesiva; análisis incompleto.') from None
    return {'nodos':nodos,'modelos':modelos,'satisfacible':bool(modelos),'completo':True}

BG='#0e1625';PANEL='#172237';TEXT='#e5edf7';MUTED='#98acc4';ACCENT='#35d6ba'
def caja(parent,**kwargs):
    return scrolledtext.ScrolledText(parent,bg='#101c2e',fg=TEXT,insertbackground=ACCENT,selectbackground='#28566a',relief='flat',padx=12,pady=10,font=('Consolas',11),**kwargs)

def tabla(parent,cols,widths):
    f=ttk.Frame(parent);f.pack(fill='both',expand=True)
    t=ttk.Treeview(f,columns=cols,show='headings',selectmode='browse')
    for k,w in zip(cols,widths):t.heading(k,text=k);t.column(k,width=w,stretch=k==cols[-1])
    sy=ttk.Scrollbar(f,orient='vertical',command=t.yview);sx=ttk.Scrollbar(f,orient='horizontal',command=t.xview)
    t.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);sy.pack(side='right',fill='y');sx.pack(side='bottom',fill='x');t.pack(fill='both',expand=True)
    return t

class VistaArbol(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent);self.datos=[];self.escala=1.;self.base_coords={};self.fit_mode=True
        bar=ttk.Frame(self,padding=8);bar.pack(fill='x')
        for texto,fn in [('− Alejar',lambda:self.zoom(self.escala/1.2)),('+ Acercar',lambda:self.zoom(self.escala*1.2)),('Ver completo',self.ajustar),('100%',lambda:self.zoom(1))]:ttk.Button(bar,text=texto,command=fn).pack(side='left',padx=3)
        self.porcentaje=tk.StringVar(value='100%');ttk.Label(bar,textvariable=self.porcentaje).pack(side='left',padx=12)
        ttk.Label(bar,text='Rueda: zoom · Arrastrar: mover · Clic en nodo: detalle').pack(side='left')
        area=ttk.Frame(self);area.pack(fill='both',expand=True)
        self.c=tk.Canvas(area,bg='#101927',highlightthickness=0)
        sy=ttk.Scrollbar(area,orient='vertical',command=self.c.yview);sx=ttk.Scrollbar(area,orient='horizontal',command=self.c.xview)
        self.c.configure(yscrollcommand=sy.set,xscrollcommand=sx.set);sy.pack(side='right',fill='y');sx.pack(side='bottom',fill='x');self.c.pack(fill='both',expand=True)
        self.detalle=caja(self,height=4,wrap='word');self.detalle.pack(fill='x',padx=8,pady=8)
        self.c.bind('<MouseWheel>',self.rueda);self.c.bind('<Button-4>',self.rueda);self.c.bind('<Button-5>',self.rueda)
        self.c.bind('<ButtonPress-1>',self.iniciar_arrastre);self.c.bind('<B1-Motion>',lambda e:self.c.scan_dragto(e.x,e.y,gain=1))
        self.c.bind('<Configure>',lambda e:self.ajustar() if self.fit_mode and self.datos else None)
    def iniciar_arrastre(self,e):
        self.c.scan_mark(e.x,e.y)
        ids=self.c.find_withtag('current')
        if ids:
            for tag in self.c.gettags(ids[0]):
                if tag.startswith('nodo_'):self.ver_detalle(int(tag[5:]));break
    def ver_detalle(self,i):
        n=self.datos[i];self.detalle.delete('1.0','end')
        texto=f"Nodo {i+1} · {n['estado'].upper()}\n"+'; '.join(n['nuevas'])
        if n['aplicada']:texto+='\n✓ Aplicada: '+n['aplicada']
        if n['contradiccion']:texto+='\n✕ Contradicción: '+n['contradiccion']+' y ¬'+n['contradiccion']
        self.detalle.insert('1.0',texto)
    def cargar(self,result):
        self.datos=result['nodos'];self.c.delete('all');self.base_coords={};self.escala=1
        posiciones={};depths={};hoja=0
        for n in self.datos:depths[n['id']]=0 if n['padre'] is None else depths[n['padre']]+1
        for n in reversed(self.datos):
            if n['hijos']:x=sum(posiciones[h][0] for h in n['hijos'])/len(n['hijos'])
            else:x=160+hoja*320;hoja+=1
            posiciones[n['id']]=(x,100+depths[n['id']]*150)
        for n in self.datos:
            i=n['id'];x,y=posiciones[i]
            if n['padre'] is not None:
                px,py=posiciones[n['padre']];self.c.create_line(px,py+54,x,y-54,fill='#58708e',width=2)
            color={'cerrada':'#5b273c','abierta':'#135447','expandida':'#223a58'}[n['estado']]
            self.c.create_rectangle(x-145,y-54,x+145,y+54,fill=color,outline='#6d829c',tags=('nodo_'+str(i),))
            texto='; '.join(n['nuevas'])
            if len(texto)>100:texto=texto[:97]+'…'
            final='✓ '+n['aplicada'] if n['aplicada'] else '✕ CERRADA' if n['contradiccion'] else 'ABIERTA'
            if len(final)>70:final=final[:67]+'…'
            self.c.create_text(x,y,text=f'N{i+1}  |  '+texto+'\n'+final,width=270,fill=TEXT,font=('Arial',10),tags=('nodo_'+str(i),))
        self.base_coords={i:self.c.coords(i) for i in self.c.find_all()}
        self.ver_detalle(0);self.fit_mode=True;self.after_idle(self.ajustar)
    def rueda(self,e):
        direccion=1 if getattr(e,'num',0)==4 or getattr(e,'delta',0)>0 else -1
        self.zoom(self.escala*(1.2 if direccion>0 else 1/1.2),e.x,e.y);return 'break'
    def zoom(self,valor,x=None,y=None,ajuste=False):
        if not self.base_coords:return
        self.fit_mode=ajuste;x=self.c.winfo_width()/2 if x is None else x;y=self.c.winfo_height()/2 if y is None else y
        nuevo=max(.00001,min(5.,valor));f=nuevo/self.escala
        wx=self.c.canvasx(x)*f;wy=self.c.canvasy(y)*f;self.escala=nuevo
        for i,coords in self.base_coords.items():
            self.c.coords(i,*[v*nuevo for v in coords])
            if self.c.type(i)=='text':self.c.itemconfigure(i,font=('Arial',max(1,round(10*nuevo))),width=max(1,270*nuevo),state='hidden' if nuevo<.08 else 'normal')
        b=self.c.bbox('all');r=(b[0]-30,b[1]-30,b[2]+30,b[3]+30);self.c.configure(scrollregion=r)
        self.c.xview_moveto((wx-x-r[0])/max(1,r[2]-r[0]));self.c.yview_moveto((wy-y-r[1])/max(1,r[3]-r[1]))
        self.porcentaje.set(f'{nuevo*100:.1f}%')
    def ajustar(self):
        if not self.datos:return
        coords=[v for i,vs in self.base_coords.items() if self.c.type(i)=='rectangle' for v in vs]
        xs=coords[::2];ys=coords[1::2]
        scale=min(max(1,self.c.winfo_width()-80)/max(1,max(xs)-min(xs)),max(1,self.c.winfo_height()-80)/max(1,max(ys)-min(ys)))
        self.zoom(scale,ajuste=True);self.c.xview_moveto(0);self.c.yview_moveto(0)

class Aplicacion(tk.Tk):
    def __init__(self,ruta=ARCHIVO):
        super().__init__();self.title('Saulo · Sistemas expertos · 23310404');self.geometry('1280x820');self.minsize(1000,650);self.configure(bg=BG)
        self.base=BaseDeConocimiento(ruta);self.resultado=None;self.trabajando=False;self.cancelar=threading.Event()
        s=ttk.Style(self);s.theme_use('clam')
        s.configure('.',background=BG,foreground=TEXT,font=('Segoe UI',10))
        s.configure('TButton',background='#23354d',foreground=TEXT,padding=(12,9),borderwidth=0)
        s.map('TButton',background=[('active','#355475'),('disabled','#172237')])
        s.configure('Accent.TButton',background='#137f71',font=('Segoe UI',10,'bold'))
        s.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground=TEXT,rowheight=30,borderwidth=0)
        s.configure('Treeview.Heading',background='#253953',foreground=TEXT,padding=8)
        s.map('Treeview',background=[('selected','#225e67')])
        s.configure('TNotebook',background=BG,borderwidth=0);s.configure('TNotebook.Tab',padding=(20,12),background=PANEL)
        s.map('TNotebook.Tab',background=[('selected','#246777')])
        side=tk.Frame(self,bg=PANEL,width=245);side.pack(side='left',fill='y');side.pack_propagate(False)
        tk.Label(side,text='SAULO',font=('Segoe UI',29,'bold'),bg=PANEL,fg=ACCENT).pack(anchor='w',padx=22,pady=(30,0))
        tk.Label(side,text='SISTEMAS EXPERTOS\nRegistro 23310404',font=('Segoe UI',11),justify='left',bg=PANEL,fg=TEXT).pack(anchor='w',padx=24,pady=(4,25))
        self.buttons=[]
        for label,fn in [('Analizar y guardar',self.analizar),('Construir árbol',self.construir),('Abrir reglas .txt',self.abrir_texto),('Ver conectores',self.ver_conectores),('Cargar ejemplos',self.ejemplos),('Exportar base JSON',self.exportar_base),('Exportar análisis',self.exportar_analisis),('Reiniciar base',self.reiniciar)]:
            b=ttk.Button(side,text=label,command=fn,style='Accent.TButton' if label=='Construir árbol' else 'TButton');b.pack(fill='x',padx=18,pady=5);self.buttons.append(b)
        ttk.Button(side,text='Cancelar cálculo',command=self.cancelar.set).pack(fill='x',padx=18,pady=5)
        self.contador=tk.StringVar();tk.Label(side,textvariable=self.contador,bg=PANEL,fg=ACCENT,justify='left',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=24,pady=20)
        tk.Label(side,text='∧   ∨   ¬   →   ↔\nLógica proposicional',bg=PANEL,fg=MUTED,font=('Segoe UI',12)).pack(side='bottom',pady=25)
        body=ttk.Frame(self,padding=18);body.pack(side='left',fill='both',expand=True)
        ttk.Label(body,text='Laboratorio de reglas',font=('Segoe UI',23,'bold')).pack(anchor='w')
        ttk.Label(body,text='Saulo Jaziel Tejeda Valle · Base de conocimiento y tableaux semánticos',foreground=MUTED).pack(anchor='w',pady=(3,15))
        self.tabs=ttk.Notebook(body);self.tabs.pack(fill='both',expand=True)
        self.tab_base=ttk.Frame(self.tabs,padding=12);self.tabs.add(self.tab_base,text='01  Base de conocimiento')
        self.arbol=VistaArbol(self.tabs);self.tabs.add(self.arbol,text='02  Árbol semántico')
        self.tab_modelos=ttk.Frame(self.tabs,padding=12);self.tabs.add(self.tab_modelos,text='03  Modelos')
        self.tabla_modelos=tabla(self.tab_modelos,('Rama / nodo','Asignaciones'),(140,900))
        ttk.Label(self.tab_modelos,text='V: verdadero · F: falso · Libre: cualquiera de los dos valores',foreground=MUTED).pack(anchor='w',pady=10)
        # Distribución estable: las tablas no pueden colapsar el editor al abrir.
        pane=ttk.Frame(self.tab_base);pane.pack(fill='both',expand=True)
        pane.rowconfigure(0,weight=1)
        pane.columnconfigure(0,weight=2,minsize=300)
        pane.columnconfigure(1,weight=3,minsize=300)
        editor=ttk.Frame(pane,width=360);results=ttk.Frame(pane,width=480)
        editor.pack_propagate(False);results.pack_propagate(False)
        editor.grid(row=0,column=0,sticky='nsew');results.grid(row=0,column=1,sticky='nsew')
        ttk.Label(editor,text='ENTRADA EN ESPAÑOL',foreground=ACCENT,font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(0,8))
        ttk.Label(editor,text='Una regla o hecho por línea. Se admiten Y, O, NO, SI, SI Y SOLO SI,\nCUANDO, IMPLICA, SOLO SI, A MENOS QUE y expresiones equivalentes.',foreground=MUTED,wraplength=340).pack(anchor='w')
        self.entrada=caja(editor,height=14,width=34,wrap='word');self.entrada.pack(fill='both',expand=True,pady=10,padx=(0,12))
        ttk.Button(editor,text='Vaciar entrada',command=lambda:self.entrada.delete('1.0','end')).pack(anchor='w')
        ttk.Label(editor,text='Ejemplos: «Si llueve, llevo paraguas»; «Trabajo si estudio»; «Llueve o nieva».\nUsa comillas si el texto del átomo contiene «y» u «o» literal.',wraplength=320,foreground=MUTED).pack(anchor='w',pady=12)
        vertical=ttk.Panedwindow(results,orient='vertical');vertical.pack(fill='both',expand=True)
        a=ttk.Frame(vertical);r=ttk.Frame(vertical);vertical.add(a,weight=1);vertical.add(r,weight=2)
        ttk.Label(a,text='ÁTOMOS',foreground=ACCENT).pack(anchor='w',pady=5);self.atomos=tabla(a,('Letra','Proposición'),(65,500))
        ttk.Label(r,text='REGLAS Y FÓRMULAS',foreground=ACCENT).pack(anchor='w',pady=5);self.reglas=tabla(r,('Regla','Fórmula','Texto original'),(65,280,600))
        self.reglas.bind('<Double-1>',self.detalle_regla)
        self.estado=tk.StringVar(value='Listo. Escribe reglas y pulsa Analizar y guardar.')
        self.tabs.pack_forget()
        ttk.Label(body,textvariable=self.estado,foreground=ACCENT,wraplength=950).pack(side='bottom',fill='x',pady=(12,0))
        self.tabs.pack(fill='both',expand=True)
        self.actualizar();self.protocol('WM_DELETE_WINDOW',self.cerrar)
    def cerrar(self):self.cancelar.set();self.destroy()
    def actualizar(self):
        for t in (self.atomos,self.reglas):t.delete(*t.get_children())
        for a,s in self.base.atomos.items():self.atomos.insert('','end',values=(a,s))
        for r in self.base.reglas:self.reglas.insert('','end',values=(r['id'],r['formula'],r['texto']))
        self.contador.set(f'{len(self.base.atomos)} átomos\n{len(self.base.reglas)} reglas')
    def invalidar(self):
        self.resultado=None;self.arbol.datos=[];self.arbol.base_coords={};self.arbol.c.delete('all');self.arbol.detalle.delete('1.0','end');self.tabla_modelos.delete(*self.tabla_modelos.get_children())
    def analizar(self):
        if self.trabajando:return
        try:nuevas=self.base.agregar_lote(self.entrada.get('1.0','end'))
        except (ValueError,OSError) as e:messagebox.showerror('Revisa la entrada',str(e));return
        self.invalidar();self.actualizar();self.entrada.delete('1.0','end');self.estado.set(f'{len(nuevas)} reglas guardadas. Puedes construir el árbol de la base completa.')
    def ejemplos(self):
        if self.trabajando:return
        self.entrada.delete('1.0','end')
        self.entrada.insert('1.0',
            'Si Juan estudia y entrega la tarea, entonces aprueba el examen\n'
            'Juan estudia\n'
            'Juan entrega la tarea\n'
            'Juan aprueba el examen si y solo si Juan obtiene una calificación aprobatoria\n'
            'no Juan reprueba el examen\n'
            'Juan recibe su certificado solo si Juan aprueba el examen\n'
            'Juan hace práctica o bien Juan realiza proyecto')
        self.tabs.select(self.tab_base)

    def abrir_texto(self):
        if self.trabajando:return
        destino=filedialog.askopenfilename(title='Abrir reglas',filetypes=[('Texto plano','*.txt'),('Todos','*.*')])
        if not destino:return
        try:
            contenido=Path(destino).read_text(encoding='utf-8-sig')
        except (OSError,UnicodeError) as e:
            messagebox.showerror('Error al abrir TXT',str(e));return
        self.entrada.delete('1.0','end');self.entrada.insert('1.0',contenido)
        self.tabs.select(self.tab_base)
        self.estado.set('TXT cargado en el editor. Revisa el texto y pulsa Analizar y guardar.')

    def ver_conectores(self):
        mensaje=(
            'CONJUNCIÓN (∧): y, e, además, pero, aunque, asimismo, así como.\n'
            'Ejemplo: llueve y hace frío\n\n'
            'DISYUNCIÓN (∨): o, u, o bien, a menos que, salvo que.\n'
            'Ejemplo: llueve o nieva\n\n'
            'NEGACIÓN (¬): no, tampoco, es falso que, no es cierto que.\n'
            'Ejemplo: Juan no estudia   /   no (llueve o nieva)\n\n'
            'IMPLICACIÓN (→):\n'
            'Si A entonces B   =   A → B\n'
            'Si A, B             =   A → B\n'
            'Cuando A, B         =   A → B\n'
            'A implica B         =   A → B\n'
            'A si B              =   B → A\n'
            'A solo si B         =   A → B\n'
            'Solo si, B, A       =   A → B\n'
            'Solo si B, A        =   A → B\n\n'
            'BICONDICIONAL (↔): si y solo si, equivale a.\n'
            'Ejemplo: A si y solo si B\n\n'
            'PARENTESIS: no (llueve y hace frío)\n'
            'COMILLAS: "Juan y María estudian" o "Juan descansa"\n\n'
            'El analizador usa español controlado: algunas oraciones ambiguas\n'
            'requieren paréntesis o reescritura. Las expresiones «a menos que»\n'
            'y «salvo que» se interpretan como disyunción inclusiva.')
        messagebox.showinfo('Guía de conectores admitidos',mensaje)

    def construir(self):
        if self.trabajando:return
        if self.entrada.get('1.0','end').strip():
            messagebox.showinfo('Entrada pendiente','Pulsa Analizar y guardar para incluir el texto nuevo.');return
        if not self.base.reglas:messagebox.showinfo('Base vacía','Agrega reglas o hechos primero.');return
        self.invalidar();self.trabajando=True;self.cancelar.clear();cola=queue.Queue()
        for b in self.buttons:b.state(['disabled'])
        self.estado.set('Construyendo árbol… El cálculo se puede cancelar.')
        formulas=[r['formula'] for r in self.base.reglas]
        def worker():
            try:cola.put(('ok',construir_tableau([AnalizadorRecursivo(s,True).analizar() for s in formulas],self.cancelar)))
            except Exception as e:cola.put(('error',str(e)))
        threading.Thread(target=worker,daemon=True).start()
        def revisar():
            try:tipo,data=cola.get_nowait()
            except queue.Empty:self.after(80,revisar);return
            self.trabajando=False
            for b in self.buttons:b.state(['!disabled'])
            if tipo=='error':self.estado.set(data);messagebox.showwarning('Análisis incompleto',data);return
            self.resultado=data;self.tabs.select(self.arbol);self.arbol.cargar(data)
            for i,m in enumerate(data['modelos'],1):
                valores=m['valores'];texto=', '.join(f"{a} = {'V' if valores[a] else 'F'}" if a in valores else f'{a} = Libre' for a in self.base.atomos)
                self.tabla_modelos.insert('','end',values=(f"{i} / N{m['nodo']+1}",texto))
            self.estado.set(f"Base satisfacible · {len(data['modelos'])} ramas abiertas · {len(data['nodos'])} nodos" if data['satisfacible'] else 'Base insatisfacible: todas las ramas están cerradas (✕).')
        self.after(80,revisar)
    def detalle_regla(self,e=None):
        ids=self.reglas.selection()
        if ids:
            a,f,t=self.reglas.item(ids[0],'values');messagebox.showinfo(a,f'{t}\n\n{f}')
    def exportar_base(self):self.exportar({'atomos':self.base.atomos,'reglas':self.base.reglas})
    def exportar_analisis(self):
        if self.resultado is None:messagebox.showinfo('Sin análisis','Construye primero el árbol.');return
        self.exportar({'atomos':self.base.atomos,'reglas':self.base.reglas,**self.resultado})
    def exportar(self,data):
        path=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON','*.json')])
        if path:
            try:Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            except OSError as e:messagebox.showerror('No se pudo exportar',str(e))
    def reiniciar(self):
        if self.trabajando:return
        if messagebox.askyesno('Reiniciar base','¿Eliminar todas las reglas y átomos de esta base?'):
            prev=self.base.atomos,self.base.reglas;self.base.atomos={};self.base.reglas=[]
            try:self.base.guardar()
            except OSError as e:self.base.atomos,self.base.reglas=prev;messagebox.showerror('Error',str(e));return
            self.invalidar();self.actualizar();self.estado.set('Base vacía. Lista para nuevas reglas.')

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--consola',action='store_true');p.add_argument('--demo',action='store_true');args=p.parse_args()
    if not args.consola and not args.demo:
        try:app=Aplicacion();app.mainloop()
        except (ValueError,KeyError,OSError,json.JSONDecodeError) as e:
            messagebox.showerror('No se pudo abrir la base',str(e)+'\nEl archivo original no fue borrado.')
        return
    base=BaseDeConocimiento()
    if args.demo:
        for s in ['Si es de día, entonces voy a trabajar','es de día']:base.agregar(s)
        print(base.mostrar());return
    print('SAULO · SISTEMAS EXPERTOS | :ver, :arbol, :salir')
    while True:
        try:s=input('Regla > ').strip()
        except (EOFError,KeyboardInterrupt):break
        if s in {':salir','salir',':q'}:break
        try:
            if s==':ver':print(base.mostrar())
            elif s==':arbol':print(json.dumps(construir_tableau([AnalizadorRecursivo(r['formula'],True).analizar() for r in base.reglas]),ensure_ascii=False,indent=2))
            elif s:print(base.agregar(s))
        except (ValueError,OSError,AnalisisInterrumpido) as e:print(e)
if __name__=='__main__':main()
