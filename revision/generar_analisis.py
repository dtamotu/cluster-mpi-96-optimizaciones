#!/usr/bin/env python3
"""Análisis descriptivo adicional: solo lee las 118 corridas conservadas.

No ejecuta MPI. Exporta cada cifra derivada a JSON y el catálogo de corridas
a CSV para que el informe pueda revisarse sin extraer números del PDF.
"""
from __future__ import annotations
import csv
import json
import statistics as st
from pathlib import Path
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from generar_optimizacion import cargar, OUT, ROOT

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42})
COLORS = ["#244F73", "#B86236", "#257F78", "#806295"]
rows, groups = cargar()
assert len(rows) == 118 and all(r["estado"] == "ok" for r in rows)
assert len({r['id'] for r in rows}) == 118
for r in rows:
    r['_meta'] = json.JSONDecoder().raw_decode(r['_log'].read_text())[0]

def group(kind, red, n, p, nodes, variant):
    return sorted(groups[(kind, red, n, p, nodes, variant)], key=lambda r: int(r['repeticion']))

def vals(g, field=None):
    field = field or ('T_Bcast' if g[0]['kind'] == 'bcast' else 'T_Total')
    return [float(r[field]) for r in g]

def med(g, field=None):
    return st.median(vals(g, field))

def savefig(name):
    plt.savefig(OUT / 'img' / (name + '.pdf'), bbox_inches='tight')
    plt.savefig(OUT / 'img' / (name + '.png'), bbox_inches='tight', dpi=150)
    plt.close()

def tex_table(name, columns, header, lines):
    (OUT / 'tablas' / (name + '.tex')).write_text(
        '\\begin{center}\\small\n\\begin{tabular}{' + columns + '}\n\\toprule\n' + header +
        ' \\\\\n\\midrule\n' + '\n'.join(' & '.join(map(str, line)) + ' \\\\' for line in lines) +
        '\n\\bottomrule\n\\end{tabular}\n\\end{center}\n')

def points(ax, gs, labels, ylabel='Tiempo interno (s)', log=False):
    for i, g in enumerate(gs):
        v = vals(g)
        ax.scatter(np.linspace(i-.11, i+.11, len(v)), v, color=COLORS[i % 4], s=30, zorder=3)
        ax.plot([i-.25, i+.25], [st.median(v)]*2, color=COLORS[i % 4], lw=2.5)
    ax.set_xticks(range(len(gs)), labels)
    if log:
        ax.set_yscale('log')
    else:
        ax.set_ylim(bottom=0)
    ax.set_ylabel(ylabel)
    ax.grid(axis='y', alpha=.2)

# Todas las observaciones de las comparaciones principales, sin quitar atípicos.
fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
for i, red in enumerate(('Ethernet', 'Wi-Fi')):
    for j, p in enumerate((24, 96)):
        gs = [group('matriz', red, 3072, p, 1 if p == 24 else 4, v) for v in ('1d', '1d-hier')]
        points(axes[j, i], gs, ['1D global', '1D jerárquica'])
        axes[j, i].set_title(f'{red} · P={p} · {1 if p == 24 else 4} nodo(s)')
savefig('analisis_repeticiones')

fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), constrained_layout=True)
for ax, red in zip(axes, ('Ethernet', 'Wi-Fi')):
    gs = [group('bcast', red, 3072, 16, 4, v) for v in ('world', 'hier', 'tuned-knomial', 'tuned-scatter')]
    points(ax, gs, ['Global', 'Jerárquica', 'Knomial', 'Scatter'], log=True)
    ax.set_title(red)
savefig('analisis_bcast_puntos')

# Razones de medianas y razones dentro de cada bloque aleatorizado.
ratios = []
for red in ('Ethernet', 'Wi-Fi'):
    for kind, p, va, vb in [('matriz', 96, '1d', '1d-hier'), ('bcast', 16, 'world', 'hier'),
                              ('bcast', 16, 'hier', 'tuned-knomial'), ('matriz', 64, '2d', '1d')]:
        a, b = [group(kind, red, 3072, p, 4, v) for v in (va, vb)]
        assert [r['repeticion'] for r in a] == [r['repeticion'] for r in b]
        pair = [x/y for x, y in zip(vals(a), vals(b))]
        ratios.append(dict(prueba=kind, red=red, p=p, A=va, B=vb, repeticiones=len(a),
                           mediana_a=med(a), mediana_b=med(b), razon_medianas=med(a)/med(b),
                           reduccion_tiempo_pct=100*(1-med(b)/med(a)), ahorro_s=med(a)-med(b),
                           reduccion_tx_pct=100*(1-med(b,'tx_mb_total')/med(a,'tx_mb_total')),
                           razones_bloque=pair, razon_bloque_mediana=st.median(pair)))
tex_table('analisis_efectos', 'llrrrr',
          'Red y $P$ & A / B & $\\tilde T_A/\\tilde T_B$ & Ahorro (s) & Tiempo $\\downarrow$ & TX $\\downarrow$',
          [[f"{r['red']} {r['p']}", f"{r['A']} / {r['B']}", f"{r['razon_medianas']:.2f}",
            f"{r['ahorro_s']:.3f}", f"{r['reduccion_tiempo_pct']:.1f}\\%", f"{r['reduccion_tx_pct']:.1f}\\%"] for r in ratios])
tex_table('analisis_bloques', 'llrrr',
          'Red y $P$ & A / B & Mínimo $T_{A,j}/T_{B,j}$ & Mediana & Máximo',
          [[f"{r['red']} {r['p']}", f"{r['A']} / {r['B']}", f"{min(r['razones_bloque']):.3f}",
            f"{r['razon_bloque_mediana']:.3f}", f"{max(r['razones_bloque']):.3f}"] for r in ratios])

# TX físico por nodo. Mediana de cada nodo, no suma de medianas como total.
nodal = []
for red in ('Ethernet', 'Wi-Fi'):
    for kind, p, variants in [('matriz', 96, ('1d','1d-hier')), ('bcast',16,('world','hier','tuned-knomial'))]:
        for v in variants:
            g = group(kind, red, 3072, p, 4, v)
            hosts = list(g[0]['_meta']['antes'])
            tx = [st.median([(r['_meta']['despues'][h][0]-r['_meta']['antes'][h][0])/1e6 for r in g]) for h in hosts]
            nodal.append(dict(red=red, prueba=kind, p=p, variante=v, tx_nodos_mb=tx,
                              tx_total_mediana_mb=med(g,'tx_mb_total')))
tex_table('analisis_nodos', 'llrrrrr',
          'Red & Prueba / variante & Servidor & W1 & W2 & W4 & Total',
          [[r['red'], ('M96 ' if r['prueba']=='matriz' else 'B16 ')+r['variante'],
            *[f'{x:.1f}' for x in r['tx_nodos_mb']], f"{r['tx_total_mediana_mb']:.1f}"] for r in nodal])
fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
for ax, red in zip(axes, ('Ethernet','Wi-Fi')):
    ss = [r for r in nodal if r['red']==red and r['prueba']=='bcast']
    for i, r in enumerate(ss):
        ax.bar(np.arange(4)+(i-1)*.25, r['tx_nodos_mb'], .23, label=r['variante'], color=COLORS[i])
    ax.set_xticks(range(4), ['Servidor','Workers1','Workers2','Workers4'])
    ax.set_ylabel('TX por interfaz (MB)')
    ax.set_title(red)
    ax.grid(axis='y', alpha=.2)
axes[0].legend(fontsize=8)
savefig('analisis_tx_nodos')

phase = []
for red in ('Ethernet','Wi-Fi'):
    for v in ('1d','1d-hier'):
        g = group('matriz',red,3072,96,4,v)
        phase.append([red,v,*[f'{med(g,c):.3f}' for c in ('T_Scatter','T_Bcast','T_Calc','T_Gather','T_Total')]])
tex_table('analisis_fases', 'llrrrrr', 'Red & Variante & Scatter & Bcast & Cálculo & Gather & Total', phase)

wall=[]
for kind,red,n,p,nodes,v in [('matriz','Ethernet',3072,24,1,'1d'),('matriz','Ethernet',3072,96,4,'1d'),
 ('matriz','Ethernet',3072,96,4,'1d-hier'),('matriz','Wi-Fi',3072,96,4,'1d'),
 ('matriz','Wi-Fi',3072,96,4,'1d-hier'),('trapecio','Ethernet',10**8,24,1,'simetrico'),
 ('trapecio','Ethernet',10**8,96,4,'simetrico'),('trapecio','Ethernet',10**11,24,1,'simetrico'),
 ('trapecio','Ethernet',10**11,96,4,'simetrico')]:
    g=group(kind,red,n,p,nodes,v)
    delta=st.median([float(r['pared_s'])-float(r['T_Total']) for r in g])
    wall.append(dict(kind=kind,red=red,n=n,p=p,variante=v,interno=med(g),pared=med(g,'pared_s'),
                     diferencia_mediana=delta))
tex_table('analisis_pared', 'llrlrrr', 'Prueba / tamaño & Red & $P$ & Variante & Interno (s) & Pared (s) & $\\Delta$ (s)',
 [[('M3072' if r['kind']=='matriz' else ('$n=10^8$' if r['n']==10**8 else '$n=10^{11}$')),r['red'],r['p'],r['variante'],
   f"{r['interno']:.6f}",f"{r['pared']:.3f}",f"{r['diferencia_mediana']:.3f}"] for r in wall])

# Memoria de las reservas explícitas del código; no es RSS medido.
memory=[]
for n in (3072,6144,7168):
    m=8*n*n
    for p,h in ((24,1),(96,4)):
        r=p//h
        rowcounts=[n//p+(i<n%p) for i in range(p)]
        pernode=[r*m+16*n*sum(rowcounts[i*r:(i+1)*r])+(2*m if i==0 else 0) for i in range(h)]
        memory.append(dict(n=n,p=p,nodos=h,matriz_mb=m/1e6,servidor_gib=pernode[0]/2**30,
                           worker_max_gib=max(pernode[1:],default=0)/2**30))
tex_table('analisis_memoria', 'rrrrrr', '$N$ & $P$ & Nodos & Una matriz (MB) & Servidor (GiB) & Worker máx. (GiB)',
 [[r['n'],r['p'],r['nodos'],f"{r['matriz_mb']:.3f}",f"{r['servidor_gib']:.3f}",
   f"{r['worker_max_gib']:.3f}" if r['nodos']>1 else '--'] for r in memory])

fig, ax=plt.subplots(figsize=(8.2,3.7), constrained_layout=True)
grid=np.arange(64).reshape(8,8)
from matplotlib.colors import ListedColormap
ax.imshow(grid//16,cmap=ListedColormap(['#DFEAF1','#F2E2D7','#DCEFEA','#E6DEF0']),vmin=0,vmax=3)
for i in range(8):
    for j in range(8):
        ax.text(j,i,str(grid[i,j]),ha='center',va='center',fontsize=9)
ax.set_xticks(range(8));ax.set_yticks(range(8));ax.set_xlabel('Columna de la malla');ax.set_ylabel('Fila de la malla')
ax.set_aspect('auto')
for y,label in zip((.5,2.5,4.5,6.5),('Servidor','Workers1','Workers2','Workers4')):
    ax.text(7.65,y,label,va='center',fontsize=10)
ax.set_xlim(-.5,10.5)
ax.set_title('P=64 · malla 8 × 8 · 16 rangos consecutivos por nodo')
savefig('analisis_malla')

fig,axes=plt.subplots(2,2,figsize=(9,6.5), constrained_layout=True)
for i,n in enumerate((10**8,10**11)):
    for j,p in enumerate((24,96)):
        gs=[group('trapecio','Ethernet',n,p,1 if p==24 else 4,v) for v in ('simetrico','asimetrico')]
        points(axes[i,j],gs,['Simétrico','Ponderado'])
        axes[i,j].set_title(f'n=10^{8 if n==10**8 else 11} · P={p}')
savefig('analisis_trapecio')

# Catálogo con rutas relativas, métricas sin redondeo nuevo y colocación explícita.
catalog=[]
for r in rows:
    nr={k:v for k,v in r.items() if not k.startswith('_')}
    nr['log']=str(r['_log'].relative_to(OUT.parent)) if r['_log'].is_relative_to(OUT.parent) else str(r['_log'])
    nr['inicio']=r['_meta']['inicio']
    nr['reparto']=str(int(r['p'])//int(r['nodos']))+' por nodo'
    catalog.append(nr)
fields=list(dict.fromkeys(k for r in catalog for k in r))
with (OUT/'datos'/'catalogo_campana.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(catalog)
# Detalle de las 75 observaciones ampliadas, sin perder P=48 y P=72.
expanded=list(csv.DictReader((ROOT/'datos'/'ampliada'/'resultados_consolidados.csv').open()))
lines=[r'\begin{longtable}{llrrrrrrr}',
       r'\caption{Las 75 ejecuciones de la batería ampliada. Tiempos en segundos; MB = TX+RX del servidor.}\label{tab:ampliada-completa}\\',
       r'\toprule Red & Prueba & Tamaño & $P$ & Total & Distribuir & Calcular & Reunir/reducir & MB \\',
       r'\midrule\endfirsthead',
       r'\toprule Red & Prueba & Tamaño & $P$ & Total & Distribuir & Calcular & Reunir/reducir & MB \\',
       r'\midrule\endhead']
for r in expanded:
    lines.append(' & '.join([r['red'],r['experimento'],r['tamano'],r['procesos'],
                            *[f"{float(r[k]):.6f}" for k in ('T_Total','T_Dist','T_Calc','T_Gather')],
                            f"{float(r['mb_real_master']):.2f}"])+r' \\')
lines.append(r'\bottomrule\end{longtable}')
(OUT/'tablas'/'analisis_ampliada_completa.tex').write_text('\n'.join(lines)+'\n')
(OUT/'datos'/'analisis_profundo.json').write_text(json.dumps(dict(
    alcance=Counter(r['kind'] for r in rows),efectos=ratios,trafico_nodal=nodal,tiempo_pared=wall,
    memoria_modelo=memory,observaciones=118),ensure_ascii=False,indent=2)+'\n')
print('Análisis: 118 observaciones de campaña, 75 ampliadas, 5 figuras, 7 tablas y catálogo trazable.')
