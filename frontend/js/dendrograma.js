/**
 * js/dendrograma.js — Lógica D3 do dendrograma.
 * Depende de: state.js, api.js, e das funções globais do index.html
 * (showLoading, hideLoading, setContexto, updateMetricas, updateLegendaContextual)
 */

// ── Variáveis do dendrograma ──
let svg, g, treemap, root, diagonal;
let dendroI = 0;
const tipEl = () => document.getElementById('tooltip');

// ── Sistema de cores ──
const COLOR_STOPS = [
    { score: -2000, color: '#2E4A60' },
    { score: -1000, color: '#4A7299' },
    { score:  -200, color: '#5A8AB8' },
    { score:   -30, color: '#6B7F8C' },
    { score:    30, color: '#9BB8A8' },
    { score:   200, color: '#D4A06A' },
    { score:  1000, color: '#E8873D' },
    { score:  2000, color: '#E8873D' },
];

function hexToRgb(hex) {
    return {
        r: parseInt(hex.slice(1,3),16),
        g: parseInt(hex.slice(3,5),16),
        b: parseInt(hex.slice(5,7),16)
    };
}
function rgbToHex(r,g,b) {
    return '#' + [r,g,b].map(x => {
        const h = Math.round(x).toString(16);
        return h.length===1 ? '0'+h : h;
    }).join('');
}
function interpolateColor(score) {
    for (let i=0; i<COLOR_STOPS.length-1; i++) {
        const s1=COLOR_STOPS[i], s2=COLOR_STOPS[i+1];
        if (score>=s1.score && score<=s2.score) {
            const t=(score-s1.score)/(s2.score-s1.score);
            const c1=hexToRgb(s1.color), c2=hexToRgb(s2.color);
            return rgbToHex(c1.r+t*(c2.r-c1.r), c1.g+t*(c2.g-c1.g), c1.b+t*(c2.b-c1.b));
        }
    }
    return score < COLOR_STOPS[0].score ? COLOR_STOPS[0].color : COLOR_STOPS[COLOR_STOPS.length-1].color;
}

function getNodeScore(d) {
    if (!d?.data?.metrics) return 0;
    const m = d.data.metrics;
    if (d.data.leaf) return m.score_nexas || 0;
    const agg = NexasState.agregacao;
    if (agg==='median') return m.median_score || m.avg_score || 0;
    if (agg==='max')    return m.max_score    || m.avg_score || 0;
    return m.avg_score || 0;
}

function nodeColor(d) {
    if (!d?.data?.metrics) return '#6B7F8C';
    if (d.data.leaf) {
        const dir = d.data.metrics.direcao;
        if (dir==='DRIVER')      return '#E8873D';
        if (dir==='ANTI-DRIVER') return '#2E4A60';
        return '#6B7F8C';
    }
    return interpolateColor(getNodeScore(d));
}
function linkColor(d) { return interpolateColor(getNodeScore(d)); }

function getTextColor() {
    return document.documentElement.getAttribute('data-theme')==='dark' ? '#e2e8f0' : '#0f172a';
}
function getNodeStroke() {
    return document.documentElement.getAttribute('data-theme')==='dark' ? '#1e293b' : '#e2e8f0';
}
function getAgregacaoLabel() {
    return { weighted_mean:'Ponderada', mean:'Simples', median:'Mediana', max:'Máximo' }[NexasState.agregacao] || 'Ponderada';
}

function wrapText(text, maxChars=35) {
    if (!text || text.length<=maxChars) return [text||''];
    const words=text.split(' '), lines=[];
    let cur='';
    for (const w of words) {
        const t=cur ? `${cur} ${w}` : w;
        if (t.length<=maxChars) cur=t;
        else { if (cur) lines.push(cur); cur=w; }
    }
    if (cur) lines.push(cur);
    return lines;
}

// ── Tooltip ──
function showTip(ev, d) {
    const tip = tipEl();
    if (!d?.data || !tip) return;
    const m = d.data.metrics;
    if (!m) return;
    const score = getNodeScore(d);
    const scoreColor = d.data.leaf ? nodeColor(d) : interpolateColor(score);
    let h = `<div class="t-title">${d.data.name||'Sem nome'}</div>`;
    if (d.data.leaf) {
        h += `<div class="t-row">Score Nexas: <em style="color:${scoreColor};font-weight:bold">${score.toFixed(2)}</em></div>`;
        h += `<div class="t-row">Direção: <em style="color:${scoreColor};font-weight:bold">${m.direcao||'N/A'}</em></div>`;
        h += `<div class="t-row">Categoria: <em>${m.categoria_direcao||'N/A'}</em></div>`;
        h += `<div class="t-row">Lift: <em>${(m.lift||0).toFixed(3)}</em></div>`;
        h += `<div class="t-row">Relevância: <em>${((m.relevancia||0)*100).toFixed(1)}%</em></div>`;
        if (m.per_relativo != null) h += `<div class="t-row">% Relativo: <em>${m.per_relativo.toFixed(1)}%</em></div>`;
        if (m.base_comum) h += `<div class="t-row">Base comum: <em>${m.base_comum}</em></div>`;
    } else {
        h += `<div class="t-row">Score Médio (${getAgregacaoLabel()}): <em style="color:${scoreColor};font-weight:bold">${score.toFixed(2)}</em></div>`;
        if (m.min_score!=null && m.max_score!=null)
            h += `<div class="t-row">Range: <em>${m.min_score.toFixed(0)} a ${m.max_score.toFixed(0)}</em></div>`;
        if (m.median_score!=null && Math.abs(m.median_score-m.avg_score)>0.1)
            h += `<div class="t-row">Mediana: <em>${m.median_score.toFixed(2)}</em></div>`;
        if (m.composition) {
            h += `<div class="t-row" style="margin-top:.5rem;padding-top:.5rem;border-top:1px solid var(--border-color)"><strong>Composição:</strong></div>`;
            if (m.composition.drivers) {
                const dr=m.composition.drivers;
                h += `<div class="t-row">• Drivers: <em>${dr.percentage}% (${dr.count})</em></div>`;
                h += `<div class="t-row" style="margin-left:1rem">média <em style="color:#E8873D">+${dr.avg.toFixed(0)}</em>, max <em>+${dr.max.toFixed(0)}</em></div>`;
            }
            if (m.composition.anti_drivers) {
                const a=m.composition.anti_drivers;
                h += `<div class="t-row">• Anti-drivers: <em>${a.percentage}% (${a.count})</em></div>`;
                h += `<div class="t-row" style="margin-left:1rem">média <em style="color:#2E4A60">${a.avg.toFixed(0)}</em>, min <em>${a.min.toFixed(0)}</em></div>`;
            }
        }
        h += `<div class="t-row">Relevância média: <em>${((m.avg_relevancia||0)*100).toFixed(1)}%</em></div>`;
        h += `<div class="t-row">Associações: <em>${m.count||0}</em></div>`;
        h += `<div class="t-hint">Clique para expandir / colapsar</div>`;
    }
    tip.innerHTML = h;
    tip.style.opacity = '1';
    tip.style.left = `${ev.clientX+16}px`;
    tip.style.top  = `${ev.clientY-10}px`;
}
function hideTip() {
    const tip = tipEl();
    if (tip) tip.style.opacity = '0';
}

// ── Renderização ──
function renderTree(data) {
    if (!data) return;
    const container = document.getElementById('svg-container');
    if (!container) return;
    container.innerHTML = '';
    const width  = container.clientWidth;
    const height = container.clientHeight;
    svg = d3.select('#svg-container').append('svg').attr('width', width).attr('height', height);
    g   = svg.append('g');
    const zoom = d3.zoom().scaleExtent([0.1,10]).on('zoom', ev => {
        g.attr('transform', ev.transform);
        NexasState.zoomLevel = ev.transform.k;
        const el = document.getElementById('zoom-pct');
        if (el) el.textContent = Math.round(ev.transform.k*100)+'%';
    });
    svg.call(zoom);
    treemap = d3.tree().nodeSize([NexasState.nodeYSpacing, NexasState.nodeXSpacing]);
    root    = d3.hierarchy(data);
    root.x0 = height/2;
    root.y0 = 0;
    root.children?.forEach(collapse);
    update(root);
    svg.call(zoom.transform, d3.zoomIdentity.translate(100, height/2).scale(1));
}

function update(source) {
    const treeData = treemap(root);
    const nodes = treeData.descendants();
    const links = treeData.links();
    nodes.forEach(d => { d.y = d.depth * NexasState.nodeXSpacing; });

    const node = g.selectAll('g.node').data(nodes, d => d.id||(d.id=++dendroI));
    const nodeEnter = node.enter().append('g')
        .attr('class','node')
        .attr('transform', d=>`translate(${source.y0},${source.x0})`)
        .on('click', click)
        .on('mouseover', showTip)
        .on('mousemove', (ev,d) => {
            const tip=tipEl();
            if (tip) { tip.style.left=`${ev.clientX+16}px`; tip.style.top=`${ev.clientY-10}px`; }
        })
        .on('mouseout', hideTip);

    nodeEnter.append('circle').attr('r',5)
        .style('fill', d=>nodeColor(d))
        .style('stroke', getNodeStroke())
        .style('stroke-width','2px');

    nodeEnter.append('text').attr('class','node-text')
        .attr('dy','.35em')
        .attr('x', d=>d.children||d._children?-10:10)
        .attr('text-anchor', d=>d.children||d._children?'end':'start')
        .style('fill', getTextColor()).style('font-size','11px').style('font-weight','500')
        .each(function(d) {
            const lines=wrapText(d.data.name);
            const el=d3.select(this);
            lines.forEach((line,i)=> {
                el.append('tspan').attr('class','node-text-line')
                  .attr('x', d.children||d._children?-10:10)
                  .attr('dy', i===0?0:'1.1em').text(line).style('fill',getTextColor());
            });
        });

    const nodeUpdate = nodeEnter.merge(node);
    nodeUpdate.transition().duration(500).attr('transform',d=>`translate(${d.y},${d.x})`);
    nodeUpdate.select('circle').style('fill',d=>nodeColor(d)).style('stroke',getNodeStroke()).attr('r',5);

    node.exit().transition().duration(500).attr('transform',d=>`translate(${source.y},${source.x})`).remove()
        .select('circle').attr('r',0);

    diagonal = d3.linkHorizontal().x(d=>d.y).y(d=>d.x);
    const link = g.selectAll('path.link').data(links, d=>d.target.id);
    const linkEnter = link.enter().insert('path','g').attr('class','link')
        .attr('d', d=>{const o={x:source.x0,y:source.y0}; return diagonal({source:o,target:o});})
        .style('fill','none')
        .style('stroke', d=>linkColor(d.target))
        .style('stroke-width', d=>Math.max(1,Math.min(4,Math.abs(getNodeScore(d.target))/200)))
        .style('opacity',0.6);

    linkEnter.merge(link).transition().duration(500).attr('d',diagonal)
        .style('stroke',d=>linkColor(d.target))
        .style('stroke-width',d=>Math.max(1,Math.min(4,Math.abs(getNodeScore(d.target))/200)));

    link.exit().transition().duration(500)
        .attr('d',d=>{const o={x:source.x,y:source.y};return diagonal({source:o,target:o});}).remove();

    nodes.forEach(d=>{ d.x0=d.x; d.y0=d.y; });
}

function click(ev,d) {
    if (d.children) { d._children=d.children; d.children=null; }
    else { d.children=d._children; d._children=null; }
    update(d);
}
function collapse(d) {
    if (d.children) { d._children=d.children; d._children.forEach(collapse); d.children=null; }
}
function expand(d) {
    if (d._children) { d.children=d._children; d.children.forEach(expand); d._children=null; }
}

// ── Zoom ──
function zoomIn()  { if (!svg) return; svg.transition().duration(300).call(d3.zoom().transform, d3.zoomIdentity.translate(100,svg.node().clientHeight/2).scale(NexasState.zoomLevel*1.2)); }
function zoomOut() { if (!svg) return; svg.transition().duration(300).call(d3.zoom().transform, d3.zoomIdentity.translate(100,svg.node().clientHeight/2).scale(NexasState.zoomLevel/1.2)); }
function zoomFit() { if (!svg) return; svg.transition().duration(500).call(d3.zoom().transform, d3.zoomIdentity.translate(100,svg.node().clientHeight/2).scale(1)); }

function searchNodes(query) {
    if (!query||!root) { g?.selectAll('.node').classed('highlighted',false).classed('dimmed',false); return; }
    const q=query.toLowerCase();
    const nodes=root.descendants();
    const matches=nodes.filter(d=>d.data.name?.toLowerCase().includes(q));
    g.selectAll('.node').classed('dimmed',true);
    matches.forEach(m=>{ let c=m; while(c){ if(c._children){c.children=c._children;c._children=null;} c=c.parent; } });
    update(root);
    g.selectAll('.node').each(function(d){
        const isM=matches.includes(d);
        d3.select(this).classed('highlighted',isM).classed('dimmed',!isM);
    });
}

function exportPNG() {
    showLoading('Gerando PNG...');
    setTimeout(()=>{
        try {
            const svgEl=svg.node(), bbox=g.node().getBBox(), pad=40;
            const canvas=document.createElement('canvas');
            canvas.width=bbox.width+pad*2; canvas.height=bbox.height+pad*2;
            const ctx=canvas.getContext('2d');
            ctx.fillStyle=document.documentElement.getAttribute('data-theme')==='dark'?'#0f172a':'#ffffff';
            ctx.fillRect(0,0,canvas.width,canvas.height);
            const svgBlob=new Blob([new XMLSerializer().serializeToString(svgEl)],{type:'image/svg+xml;charset=utf-8'});
            const url=URL.createObjectURL(svgBlob);
            const img=new Image();
            img.onload=()=>{
                ctx.drawImage(img,pad-bbox.x,pad-bbox.y);
                canvas.toBlob(blob=>{
                    const link=document.createElement('a');
                    link.download=`nexas-dendrograma-${NexasState.onda}-${Date.now()}.png`;
                    link.href=URL.createObjectURL(blob); link.click();
                    URL.revokeObjectURL(url); hideLoading();
                });
            };
            img.src=url;
        } catch(e){ console.error(e); alert('Erro ao exportar PNG'); hideLoading(); }
    },100);
}

function resizeDendrogram() {
    if (!svg||!root) return;
    const container=document.getElementById('svg-container');
    if (!container) return;
    const w=container.clientWidth, h=container.clientHeight;
    d3.select('#svg-container svg').attr('width',w).attr('height',h);
    root.x0=h/2; root.y0=0;
    svg.transition().duration(300).call(d3.zoom().transform, d3.zoomIdentity.translate(100,h/2).scale(NexasState.zoomLevel));
    update(root);
}

function updateDendrogramaTheme() {
    if (!svg) return;
    d3.selectAll('.node-text-line').style('fill', getTextColor());
    d3.selectAll('.node circle').style('stroke', getNodeStroke());
}

// ── Init do dendrograma (chamado pelo switchTab) ──
function initDendrograma() {
    dendroI = 0;

    document.getElementById('btn-zoom-in')?.addEventListener('click', zoomIn);
    document.getElementById('btn-zoom-out')?.addEventListener('click', zoomOut);
    document.getElementById('btn-zoom-fit')?.addEventListener('click', zoomFit);

    document.getElementById('slider-y')?.addEventListener('input', e => {
        NexasState.nodeYSpacing = +e.target.value;
        document.getElementById('val-y').textContent = e.target.value;
        if (root) { treemap.nodeSize([NexasState.nodeYSpacing, NexasState.nodeXSpacing]); update(root); }
    });
    document.getElementById('slider-x')?.addEventListener('input', e => {
        NexasState.nodeXSpacing = +e.target.value;
        document.getElementById('val-x').textContent = e.target.value;
        if (root) { treemap.nodeSize([NexasState.nodeYSpacing, NexasState.nodeXSpacing]); update(root); }
    });

    document.getElementById('search-box')?.addEventListener('input', e => searchNodes(e.target.value));
    document.getElementById('btn-clear-search')?.addEventListener('click', ()=>{
        document.getElementById('search-box').value=''; searchNodes('');
    });
    document.getElementById('btn-expand')?.addEventListener('click', ()=>{
        if (root) { root.children?.forEach(expand); update(root); }
    });
    document.getElementById('btn-collapse')?.addEventListener('click', ()=>{
        if (root) { root.children?.forEach(collapse); update(root); }
    });
    document.getElementById('agregacao-select')?.addEventListener('change', e => {
        NexasState.agregacao = e.target.value;
        if (root) update(root);
    });
    document.getElementById('btn-export')?.addEventListener('click', exportPNG);
}
