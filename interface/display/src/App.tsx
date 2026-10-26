import type { CSSProperties } from 'react';
import backdrop from './assets/images/nyxos_desktop_backdrop_1791463881307.jpg';

const bars = Array.from({ length: 36 }, (_, i) => ({
  id: i,
  height: 18 + ((i * 29 + 11) % 66),
}));

export default function App() {
  return (
    <main className="display" style={{ backgroundImage: `linear-gradient(115deg, rgba(5,6,17,.95), rgba(7,8,21,.79)), url("${backdrop}")` }} aria-label="Nyxal Display: camada visual passiva">
      <div className="frame">
        <header className="topbar">
          <div className="identity">
            <div className="mark" aria-hidden="true"><span /></div>
            <div><p className="eyebrow">NYXAL <i>/</i> DISPLAY</p><h1>NYXAL</h1></div>
          </div>
          <div className="header-meta">
            <span className="index-label">VISUAL INTERFACE / 01</span>
            <span className="passive-tag"><i /> CAMADA VISUAL</span>
          </div>
        </header>

        <section className="hero" aria-label="Composição visual da Nyxal">
          <div className="grid" aria-hidden="true" />
          <div className="crosshair crosshair-top" aria-hidden="true" />
          <div className="orbit-stage" aria-hidden="true">
            <div className="orbit outer"><span className="node node-one" /><span className="node node-two" /></div>
            <div className="orbit middle"><span className="node node-three" /></div>
            <div className="orbit inner" />
            <div className="aura" />
            <div className="core"><div className="glyph"><span /><span /><span /></div></div>
            <div className="coordinate">NX <i>·</i> 00</div>
          </div>
          <div className="side side-left"><span>CAMADA</span><b>01 / APRESENTAÇÃO</b><i /><small>INTERFACE VISUAL</small></div>
          <div className="side side-right"><span>MODO</span><b>PASSIVO / 2D</b><i /><small>SEM EXECUÇÃO</small></div>
          <div className="caption">
            <p className="eyebrow">CAMADA DE APRESENTAÇÃO</p>
            <h2>Presença<span> visual.</span></h2>
            <p>A tela da Nyxal, sem um segundo agente por trás.</p>
          </div>
          <div className="visual-index" aria-hidden="true"><span>NX—VIS</span><i /><span>PASSIVE DISPLAY</span></div>
        </section>

        <footer className="bottomline">
          <div className="footer-label"><i /> <span>NYXAL DISPLAY</span><em>/</em><span>CAMADA VISUAL</span></div>
          <div className="bars" aria-hidden="true">{bars.map(bar => <span key={bar.id} style={{ '--bar': `${bar.height}%` } as CSSProperties} />)}</div>
          <span className="footer-mode">SEM CHAT · SEM AGENTE · SEM API</span>
        </footer>
      </div>
    </main>
  );
}
