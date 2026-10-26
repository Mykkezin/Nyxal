(function () {
  "use strict";

  var METRICS_REFRESH_MS = 15000;
  var WEATHER_REFRESH_MS = 10 * 60 * 1000;
  var REFLECTION_INTERVAL_MS = 3 * 60 * 60 * 1000;
  var activeView = "chat";
  var weatherTimer = null;
  var metricsTimer = null;
  var reflectionTimer = null;

  var reflections = [
    "Inteligência não é responder depressa: é saber quando medir, quando duvidar e quando mudar de ideia.",
    "Um sistema confiável não esconde o que não sabe. Ele mostra o limite, procura evidências e tenta de novo com método.",
    "Autonomia sem limites vira risco; limites sem propósito viram prisão. Engenharia boa constrói os dois com clareza.",
    "O progresso real aparece quando uma hipótese sobrevive ao teste, não quando uma ideia parece impressionante.",
    "Conhecer um assunto é conectar princípios, consequências e exceções — não apenas decorar respostas.",
    "A curiosidade abre caminhos; a disciplina transforma caminhos em resultados verificáveis.",
    "Uma máquina pode produzir muitas palavras. Compreensão útil exige contexto, memória, critérios e correção de erros.",
    "Toda métrica é uma pergunta sobre a realidade. Antes de confiar no número, confira a fonte, a unidade e o horário.",
    "A melhor automação não retira o controle da pessoa: reduz trabalho repetitivo e deixa decisões importantes explícitas.",
    "Ser consistente não significa nunca falhar; significa detectar a falha, explicar o que aconteceu e recuperar-se com segurança.",
    "O conhecimento cresce quando diferentes áreas conversam: matemática mede, ciência testa, filosofia questiona e engenharia entrega.",
    "Uma arquitetura forte prefere componentes pequenos, contratos claros e evidências a promessas grandiosas.",
    "A velocidade resolve o agora; a observabilidade ajuda a entender por que o agora aconteceu.",
    "Pensar criticamente é tratar a própria conclusão com o mesmo rigor aplicado à conclusão de outra pessoa.",
    "A memória só é útil quando recupera a informação certa, preserva sua origem e aceita ser corrigida.",
    "Não confunda uma demonstração convincente com uma capacidade comprovada. Meça o comportamento em condições reais.",
    "A segurança começa com a menor permissão necessária e continua com registro, revisão e possibilidade de revogação.",
    "Um bom modelo explica sua incerteza; um bom sistema não transforma incerteza em falsa certeza.",
    "A criatividade imagina alternativas; a avaliação separa as promissoras das apenas atraentes.",
    "Aprender é fechar o ciclo: observar, formular uma hipótese, experimentar, medir e atualizar a conclusão.",
    "A ferramenta deve servir ao objetivo. Não acrescente complexidade só porque ela parece avançada.",
    "A qualidade aparece nos detalhes que ninguém vê: recuperação, consistência, acessibilidade, privacidade e testes.",
    "O bom julgamento nasce do encontro entre evidência, contexto, experiência e humildade para rever a decisão.",
    "Automatizar uma tarefa mal compreendida apenas torna o erro mais rápido. Primeiro entenda; depois automatize.",
    "A resposta mais útil nem sempre é a mais longa. É a que melhora a decisão seguinte.",
    "Construir uma inteligência respeitável exige modelos competentes, ferramentas verificáveis, memória com proveniência e avaliação contínua.",
    "A ciência não elimina a dúvida: transforma dúvidas vagas em perguntas que podem ser testadas.",
    "A confiabilidade é acumulada em pequenas confirmações, e perdida quando uma única promessa ignora os fatos.",
    "Não basta saber o que fazer. Um sistema responsável também precisa saber o que não deve fazer e por quê.",
    "Uma boa conversa combina escuta, contexto, clareza e naturalidade — sem sacrificar a honestidade."
  ];

  function apiUrl(path) {
    var base = String(window.NYXAL_API_BASE || window.location.origin).replace(/\/+$/, "");
    return base + path;
  }

  function addStyles() {
    if (document.getElementById("nyxalVoiceConsoleStyles")) return;
    var style = document.createElement("style");
    style.id = "nyxalVoiceConsoleStyles";
    style.textContent = [
      "#nyxalVoiceConsole{position:fixed;inset:0;z-index:5;pointer-events:none;color:#e9f2ff;font:12px/1.45 Inter,system-ui,sans-serif;transition:opacity .25s ease}",
      "#nyxalVoiceConsole *{box-sizing:border-box}",
      "#nyxalVoiceConsole button,#nyxalVoiceConsole input,#nyxalVoiceConsole textarea{font:inherit}",
      "#nyxalVoiceConsole button{cursor:pointer}",
      "#nyxalVoiceConsole .nvc-top{position:absolute;top:14px;left:16px;right:16px;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;pointer-events:none}",
      "#nyxalVoiceConsole .nvc-top-left,#nyxalVoiceConsole .nvc-top-right{display:flex;align-items:center;gap:7px;flex-wrap:wrap;pointer-events:auto}",
      "#nyxalVoiceConsole .nvc-chip{display:inline-flex;align-items:center;gap:6px;min-height:27px;padding:5px 9px;border:1px solid rgba(145,190,225,.19);border-radius:999px;background:rgba(5,12,24,.66);color:#c9d9eb;backdrop-filter:blur(12px);white-space:nowrap;font-size:10px;letter-spacing:.025em}",
      "#nyxalVoiceConsole .nvc-dot{width:5px;height:5px;border-radius:50%;background:#6ee7b7;box-shadow:0 0 10px rgba(110,231,183,.7)}",
      "#nyxalVoiceConsole .nvc-metric{color:#e8f4ff;font-variant-numeric:tabular-nums}",
      "#nyxalVoiceConsole .nvc-muted{color:#8fa4ba}",
      "#nyxalVoiceConsole .nvc-button{border:1px solid rgba(125,211,252,.28);border-radius:10px;background:rgba(10,22,39,.88);color:#dff4ff;padding:9px 12px;transition:background .16s,border-color .16s}",
      "#nyxalVoiceConsole .nvc-button:hover{background:rgba(30,64,95,.92);border-color:rgba(125,211,252,.58)}",
      "#nyxalVoiceConsole .nvc-primary{background:rgba(29,105,151,.76);border-color:rgba(125,211,252,.5)}",
      "#nyxalVoiceConsole .nvc-tool-button{position:absolute;right:18px;bottom:18px;pointer-events:auto;border-radius:999px;padding:10px 15px;box-shadow:0 10px 40px rgba(0,0,0,.28)}",
      "#nyxalVoiceConsole .nvc-workspace{position:absolute;top:61px;right:18px;bottom:72px;width:min(520px,calc(100vw - 36px));max-height:calc(100vh - 135px);overflow:auto;pointer-events:auto;border:1px solid rgba(125,211,252,.23);border-radius:16px;background:rgba(4,10,21,.96);box-shadow:0 24px 100px rgba(0,0,0,.52);backdrop-filter:blur(24px);padding:14px}",
      "#nyxalVoiceConsole .nvc-workspace[hidden],#nyxalVoiceConsole [hidden]{display:none!important}",
      "#nyxalVoiceConsole .nvc-workspace-head{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:0 0 12px;border-bottom:1px solid rgba(125,211,252,.14);margin-bottom:12px}",
      "#nyxalVoiceConsole .nvc-nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}",
      "#nyxalVoiceConsole .nvc-nav button{font-size:10px;border-radius:8px;padding:7px 9px;border:1px solid rgba(148,163,184,.15);background:rgba(15,23,42,.45);color:#aebfd2}",
      "#nyxalVoiceConsole .nvc-nav button[aria-selected=true]{border-color:rgba(125,211,252,.55);background:rgba(30,92,130,.48);color:#f1faff}",
      "#nyxalVoiceConsole .nvc-pane h3{font-size:14px;color:#eff8ff;margin:0 0 7px;font-weight:600}",
      "#nyxalVoiceConsole .nvc-pane p{color:#9fb3c8;margin:0 0 11px}",
      "#nyxalVoiceConsole .nvc-field{width:100%;border:1px solid rgba(148,163,184,.24);border-radius:10px;background:rgba(2,6,15,.85);color:#e9f2ff;padding:10px 11px;outline:none;resize:vertical;min-height:46px}",
      "#nyxalVoiceConsole .nvc-field:focus{border-color:rgba(125,211,252,.65);box-shadow:0 0 0 2px rgba(56,189,248,.08)}",
      "#nyxalVoiceConsole .nvc-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:9px}",
      "#nyxalVoiceConsole .nvc-status{font-size:10px;color:#8fa4ba;margin-top:10px;overflow-wrap:anywhere}",
      "#nyxalVoiceConsole .nvc-card{border:1px solid rgba(148,163,184,.15);background:rgba(12,22,37,.65);border-radius:11px;padding:11px;margin:8px 0}",
      "#nyxalVoiceConsole .nvc-instance{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}",
      "#nyxalVoiceConsole .nvc-instance-actions{display:flex;gap:5px;flex-wrap:wrap}",
      "#nyxalVoiceConsole .nvc-instance-actions button{padding:5px 7px;font-size:10px;border-radius:7px}",
      "#nyxalVoiceConsole .nvc-image-output{margin-top:14px}",
      "#nyxalVoiceConsole .nvc-image-output img{display:block;width:100%;max-height:56vh;object-fit:contain;background:#020407;border-radius:10px;border:1px solid rgba(148,163,184,.15)}",
      "#nyxalVoiceConsole .nvc-reflection{position:absolute;left:50%;bottom:20px;transform:translateX(-50%);width:min(610px,calc(100vw - 34px));pointer-events:auto;border:1px solid rgba(125,211,252,.22);border-radius:13px;background:rgba(3,10,22,.88);backdrop-filter:blur(14px);box-shadow:0 12px 55px rgba(0,0,0,.36);padding:11px 14px}",
      "#nyxalVoiceConsole .nvc-reflection-text{color:#e6f2ff;font-size:12px;line-height:1.55;margin:4px 0 8px}",
      "#nyxalVoiceConsole .nvc-close{border:0;background:transparent;color:#91a7bd;padding:4px 7px}",
      "#nyxalVoiceSurface.is-dormant #nyxalVoiceConsole{opacity:0;pointer-events:none}",
      "@media(max-width:720px){#nyxalVoiceConsole .nvc-top{top:8px;left:8px;right:8px}#nyxalVoiceConsole .nvc-chip{font-size:9px;min-height:24px;padding:4px 7px}#nyxalVoiceConsole .nvc-top-right{max-width:100%}#nyxalVoiceConsole .nvc-workspace{top:74px;left:9px;right:9px;bottom:68px;width:auto;max-height:none;padding:11px}#nyxalVoiceConsole .nvc-tool-button{right:10px;bottom:10px}#nyxalVoiceConsole .nvc-reflection{bottom:10px;width:calc(100vw - 18px)}}"
    ].join("\n");
    document.head.appendChild(style);
  }

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function ensureConsole() {
    if (new URLSearchParams(window.location.search).get("modo") !== "voz") return false;
    var surface = document.getElementById("nyxalVoiceSurface");
    if (!surface) return false;
    if (document.getElementById("nyxalVoiceConsole")) return true;
    addStyles();

    var dock = document.createElement("section");
    dock.id = "nyxalVoiceConsole";
    dock.setAttribute("aria-label", "Indicadores e ferramentas da Nyxal");
    dock.innerHTML = [
      '<div class="nvc-top">',
        '<div class="nvc-top-left">',
          '<div class="nvc-chip"><span class="nvc-dot"></span><span>NYXAL</span><span class="nvc-muted">RESIDENTE</span></div>',
          '<div class="nvc-chip"><span id="nvcClock">--:--:--</span><span class="nvc-muted" id="nvcDate"></span></div>',
          '<div class="nvc-chip" title="Clima atual em São Paulo"><span id="nvcWeatherIcon">◌</span><span id="nvcWeatherTemp">--°</span><span class="nvc-muted" id="nvcWeatherLabel">Clima</span></div>',
        '</div>',
        '<div class="nvc-top-right" aria-label="Métricas do computador">',
          '<div class="nvc-chip"><span class="nvc-muted">CPU</span><b id="nvcCpu" class="nvc-metric">--</b></div>',
          '<div class="nvc-chip"><span class="nvc-muted">RAM</span><b id="nvcRam" class="nvc-metric">--</b></div>',
          '<div class="nvc-chip"><span class="nvc-muted">DISCO</span><b id="nvcDisk" class="nvc-metric">--</b></div>',
          '<div class="nvc-chip"><span class="nvc-muted">GPU</span><b id="nvcGpu" class="nvc-metric">--</b></div>',
          '<div class="nvc-chip"><span class="nvc-muted">TEMP</span><b id="nvcTemp" class="nvc-metric">--</b></div>',
        '</div>',
      '</div>',
      '<button id="nvcOpenTools" class="nvc-button nvc-tool-button" type="button" aria-expanded="false">Ferramentas <span class="nvc-muted">Alt+Espaço</span></button>',
      '<section id="nvcWorkspace" class="nvc-workspace" role="dialog" aria-label="Ferramentas Nyxal" hidden>',
        '<div class="nvc-workspace-head"><div><div class="nvc-muted" style="font-size:9px;letter-spacing:.16em">NYXOS • CENTRAL DE CAPACIDADES</div><strong id="nvcWorkspaceTitle">Conversa</strong></div><button id="nvcCloseTools" class="nvc-close" type="button" aria-label="Fechar ferramentas">✕</button></div>',
        '<nav class="nvc-nav" role="tablist" aria-label="Áreas da Nyxal">',
          '<button type="button" data-nvc-view="chat" role="tab" aria-selected="true">Conversa</button>',
          '<button type="button" data-nvc-view="vps" role="tab" aria-selected="false">VPS</button>',
          '<button type="button" data-nvc-view="cyber" role="tab" aria-selected="false">Cibersegurança</button>',
          '<button type="button" data-nvc-view="data" role="tab" aria-selected="false">Data Science</button>',
          '<button type="button" data-nvc-view="image" role="tab" aria-selected="false">Imagens</button>',
          '<button type="button" data-nvc-view="reflection" role="tab" aria-selected="false">Filosofia</button>',
        '</nav>',
        '<section class="nvc-pane" data-nvc-pane="chat">',
          '<h3>Conversa por texto</h3><p>Digite ou fale normalmente. A resposta continua usando o núcleo conversacional da Nyxal.</p>',
          '<form id="nvcChatForm"><textarea id="nvcChatInput" class="nvc-field" rows="3" maxlength="12000" placeholder="O que vamos investigar?"></textarea><div class="nvc-row"><button class="nvc-button nvc-primary" type="submit">Enviar mensagem</button><span class="nvc-muted">Enter envia • Shift+Enter quebra linha</span></div></form>',
          '<div id="nvcChatStatus" class="nvc-status" aria-live="polite"></div>',
        '</section>',
        '<section class="nvc-pane" data-nvc-pane="vps" hidden>',
          '<h3>VPS • máquinas virtuais locais</h3><p>Consulta o hypervisor real. Ações de ligar, desligar e reiniciar são explícitas; nenhuma máquina é destruída por estes atalhos.</p>',
          '<div id="nvcVpsStatus" class="nvc-card">Consultando hypervisor…</div><div id="nvcVpsInstances"></div>',
          '<div class="nvc-row"><button id="nvcVpsRefresh" class="nvc-button" type="button">Atualizar estado</button></div>',
          '<div id="nvcVpsMessage" class="nvc-status" aria-live="polite"></div>',
        '</section>',
        '<section class="nvc-pane" data-nvc-pane="cyber" hidden>',
          '<h3>Cibersegurança defensiva</h3><p>Revisão de código, hardening, análise de logs, modelagem de ameaças, inventário, triagem de vulnerabilidades e plano de correção em ativos autorizados.</p>',
          '<div class="nvc-card"><strong>Limite de segurança</strong><div class="nvc-status">O modo prioriza diagnóstico e defesa. Ações intrusivas, destrutivas ou com impacto operacional exigem escopo e autorização explícitos.</div></div>',
          '<div class="nvc-row"><button id="nvcCyberStart" class="nvc-button nvc-primary" type="button">Iniciar análise defensiva</button></div>',
        '</section>',
        '<section class="nvc-pane" data-nvc-pane="data" hidden>',
          '<h3>Data Science</h3><p>Exploração de dados, estatística, qualidade de dados, visualização, hipóteses, experimentos, Python e relatórios reproduzíveis.</p>',
          '<div class="nvc-card"><strong>Fluxo de trabalho</strong><div class="nvc-status">Entender a pergunta → validar os dados → analisar → testar pressupostos → explicar resultados e limitações.</div></div>',
          '<div class="nvc-row"><button id="nvcDataStart" class="nvc-button nvc-primary" type="button">Iniciar sessão de Data Science</button></div>',
        '</section>',
        '<section class="nvc-pane" data-nvc-pane="image" hidden>',
          '<h3>Gerar imagem na conversa</h3><p>Usa a capacidade visual configurada na Nyxal. É necessário ter credencial de provedor válida no ambiente do serviço.</p>',
          '<textarea id="nvcImagePrompt" class="nvc-field" rows="3" maxlength="4000" placeholder="Descreva a imagem que deseja gerar…"></textarea>',
          '<div class="nvc-row"><button id="nvcImageGenerate" class="nvc-button nvc-primary" type="button">Gerar imagem</button><span class="nvc-muted">Até 4.000 caracteres</span></div>',
          '<div id="nvcImageStatus" class="nvc-status" aria-live="polite"></div><div id="nvcImageOutput" class="nvc-image-output"></div>',
        '</section>',
        '<section class="nvc-pane" data-nvc-pane="reflection" hidden>',
          '<h3>Reflexões Nyxal</h3><p>Uma reflexão original aparece ao abrir a interface e é renovada a cada três horas enquanto ela está em execução.</p>',
          '<div id="nvcReflectionFull" class="nvc-card"></div><div class="nvc-row"><button id="nvcReflectionSpeak" class="nvc-button" type="button">Ouvir reflexão</button><button id="nvcReflectionNext" class="nvc-button" type="button">Próxima reflexão</button></div>',
        '</section>',
      '</section>',
      '<aside id="nvcReflectionCard" class="nvc-reflection" aria-live="polite" hidden><div style="display:flex;align-items:center;justify-content:space-between;gap:12px"><span class="nvc-muted" style="font-size:9px;letter-spacing:.16em">REFLEXÃO NYXAL • A CADA 3 HORAS</span><button id="nvcReflectionDismiss" type="button" class="nvc-close" aria-label="Dispensar reflexão">✕</button></div><div id="nvcReflectionText" class="nvc-reflection-text"></div><div class="nvc-row"><button id="nvcReflectionListen" type="button" class="nvc-button">Ouvir</button><button id="nvcReflectionOpen" type="button" class="nvc-button">Abrir filosofia</button></div></aside>'
    ].join("");
    surface.appendChild(dock);

    bindEvents();
    tickClock();
    updateWeather();
    refreshMetrics();
    showInitialReflection();
    if (metricsTimer === null) metricsTimer = window.setInterval(refreshMetrics, METRICS_REFRESH_MS);
    if (weatherTimer === null) weatherTimer = window.setInterval(updateWeather, WEATHER_REFRESH_MS);
    if (reflectionTimer === null) reflectionTimer = window.setInterval(checkReflectionInterval, 60000);
    return true;
  }

  function bindEvents() {
    var openButton = document.getElementById("nvcOpenTools");
    var closeButton = document.getElementById("nvcCloseTools");
    openButton.addEventListener("click", function () { toggleWorkspace(); });
    closeButton.addEventListener("click", function () { setWorkspaceOpen(false); });

    document.querySelectorAll("[data-nvc-view]").forEach(function (button) {
      button.addEventListener("click", function () { setView(button.getAttribute("data-nvc-view")); });
    });

    document.getElementById("nvcChatForm").addEventListener("submit", function (event) {
      event.preventDefault();
      sendChatFromTool();
    });
    document.getElementById("nvcChatInput").addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendChatFromTool();
      }
    });
    document.getElementById("nvcVpsRefresh").addEventListener("click", refreshVps);
    document.getElementById("nvcCyberStart").addEventListener("click", startCyberMode);
    document.getElementById("nvcDataStart").addEventListener("click", startDataMode);
    document.getElementById("nvcImageGenerate").addEventListener("click", generateImage);
    document.getElementById("nvcReflectionDismiss").addEventListener("click", function () {
      document.getElementById("nvcReflectionCard").hidden = true;
    });
    document.getElementById("nvcReflectionListen").addEventListener("click", speakCurrentReflection);
    document.getElementById("nvcReflectionOpen").addEventListener("click", function () {
      setView("reflection");
      setWorkspaceOpen(true);
    });
    document.getElementById("nvcReflectionSpeak").addEventListener("click", speakCurrentReflection);
    document.getElementById("nvcReflectionNext").addEventListener("click", function () {
      rotateReflection(true);
      renderReflectionFull();
    });
  }

  function toggleWorkspace() {
    var panel = document.getElementById("nvcWorkspace");
    setWorkspaceOpen(Boolean(panel && panel.hidden));
  }

  function setWorkspaceOpen(open) {
    var panel = document.getElementById("nvcWorkspace");
    var button = document.getElementById("nvcOpenTools");
    if (!panel || !button) return;
    panel.hidden = !open;
    button.setAttribute("aria-expanded", String(Boolean(open)));
    button.textContent = open ? "Fechar ferramentas  ✕" : "Ferramentas  Alt+Espaço";
    if (open && activeView === "vps") refreshVps();
    if (open && activeView === "reflection") renderReflectionFull();
    if (open && activeView === "chat") document.getElementById("nvcChatInput").focus();
  }

  function setView(view) {
    var known = ["chat", "vps", "cyber", "data", "image", "reflection"];
    if (known.indexOf(view) < 0) view = "chat";
    activeView = view;
    document.querySelectorAll("[data-nvc-view]").forEach(function (button) {
      button.setAttribute("aria-selected", String(button.getAttribute("data-nvc-view") === view));
    });
    document.querySelectorAll("[data-nvc-pane]").forEach(function (pane) {
      pane.hidden = pane.getAttribute("data-nvc-pane") !== view;
    });
    var titles = { chat: "Conversa", vps: "VPS", cyber: "Cibersegurança", data: "Data Science", image: "Geração visual", reflection: "Filosofia" };
    var title = document.getElementById("nvcWorkspaceTitle");
    if (title) title.textContent = titles[view] || "Ferramentas";
    if (view === "vps") refreshVps();
    if (view === "reflection") renderReflectionFull();
  }

  function sendModePrompt(prompt, statusId) {
    var status = document.getElementById(statusId);
    if (status) status.textContent = "Enviando contexto para o núcleo conversacional…";
    if (typeof window.sendNyxalMessage !== "function") {
      if (status) status.textContent = "A função de conversa não foi carregada. Atualize a interface e tente novamente.";
      return;
    }
    Promise.resolve(window.sendNyxalMessage(prompt)).then(function () {
      if (status) status.textContent = "Modo solicitado. A resposta será apresentada na conversa da Nyxal.";
      setWorkspaceOpen(false);
    }).catch(function () {
      if (status) status.textContent = "Não foi possível enviar a solicitação. Verifique a API e tente novamente.";
    });
  }

  function startCyberMode() {
    setWorkspaceOpen(false);
    sendModePrompt(
      "Ative o modo especialista de CIBERSEGURANÇA DEFENSIVA da Nyxal. Trabalhe apenas em sistemas e dados que eu possuo ou estou autorizado a avaliar. Priorize inventário, hardening, revisão de código, análise de logs, modelagem de ameaças, triagem de vulnerabilidades e plano de remediação com evidências. Antes de qualquer operação com impacto, explique o risco e peça autorização explícita. Não afirme que executou testes sem ferramentas e resultados confirmados. Comece perguntando qual ativo, código ou objetivo defensivo vamos analisar e proponha um plano verificável.",
      "nvcChatStatus"
    );
  }

  function startDataMode() {
    setWorkspaceOpen(false);
    sendModePrompt(
      "Ative o modo especialista de DATA SCIENCE da Nyxal. Conduza o trabalho com pergunta de negócio, dicionário e qualidade de dados, análise exploratória, estatística adequada, avaliação de pressupostos, visualizações legíveis, código Python reproduzível e interpretação das limitações. Preserve privacidade e não invente valores nem conclusões. Comece identificando o objetivo, as colunas disponíveis e o resultado esperado; se eu ainda não tiver dados, proponha um plano de coleta e validação.",
      "nvcChatStatus"
    );
  }

  function sendChatFromTool() {
    var input = document.getElementById("nvcChatInput");
    var status = document.getElementById("nvcChatStatus");
    var message = String(input.value || "").trim();
    if (!message) return;
    if (typeof window.sendNyxalMessage !== "function") {
      status.textContent = "O núcleo conversacional ainda não está disponível.";
      return;
    }
    input.value = "";
    status.textContent = "Processando mensagem…";
    Promise.resolve(window.sendNyxalMessage(message)).then(function () {
      status.textContent = "Mensagem enviada ao núcleo conversacional.";
    }).catch(function () {
      status.textContent = "Falha ao enviar. Confira a conexão com a API.";
    });
  }

  function refreshMetrics() {
    tickClock();
    Promise.all([
      fetch(apiUrl("/api/agent/contexto"), { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("observabilidade_http_" + r.status); return r.json(); }),
      fetch(apiUrl("/api/public/status"), { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("status_http_" + r.status); return r.json(); })
    ]).then(function (results) {
      var obs = results[0].observabilidade || {};
      var habitat = results[1].habitat || {};
      var resources = habitat.recursos || {};
      var cpu = resources.cpu || {};
      var memory = obs.memoria || resources.memoria || {};
      var disk = obs.armazenamento_home || resources.armazenamento || {};
      var gpuPack = obs.gpu || {};
      var devices = Array.isArray(gpuPack.dispositivos) ? gpuPack.dispositivos : [];
      var gpu = devices[0] || {};
      var tempsPack = obs.temperaturas || {};
      var sensors = Array.isArray(tempsPack.sensores) ? tempsPack.sensores : [];
      var temp = gpu.temperatura_celsius;
      if (temp === null || temp === undefined) {
        var values = sensors.map(function (item) { return Number(item.celsius); }).filter(function (value) { return Number.isFinite(value); });
        if (values.length) temp = Math.max.apply(null, values);
      }
      setMetric("nvcCpu", cpu.uso_percentual, "%");
      setMetric("nvcRam", memory.uso_percentual, "%");
      setMetric("nvcDisk", disk.uso_percentual, "%");
      var gpuValue = gpu.uso_percentual;
      if (gpuValue === null || gpuValue === undefined) gpuValue = gpu.vram_uso_percentual;
      setMetric("nvcGpu", gpuValue, "%");
      setMetric("nvcTemp", temp, "°C");
    }).catch(function (error) {
      ["nvcCpu", "nvcRam", "nvcDisk", "nvcGpu", "nvcTemp"].forEach(function (id) {
        var node = document.getElementById(id);
        if (node && node.textContent === "--") node.textContent = "offline";
      });
      console.warn("Nyxal console: métricas indisponíveis", error);
    });
  }

  function setMetric(id, value, unit) {
    var node = document.getElementById(id);
    if (!node) return;
    var number = Number(value);
    node.textContent = value !== null && value !== undefined && Number.isFinite(number) ? String(Math.round(number * 10) / 10) + unit : "—";
    node.title = node.textContent === "—" ? "Este sensor não forneceu uma leitura válida" : "Leitura atual; atualizada a cada 15 segundos";
  }

  function tickClock() {
    var now = new Date();
    var clock = document.getElementById("nvcClock");
    var date = document.getElementById("nvcDate");
    if (clock) clock.textContent = now.toLocaleTimeString("pt-BR", { hour12: false });
    if (date) date.textContent = now.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }).replace(".", "");
  }

  function updateWeather() {
    var temp = document.getElementById("nvcWeatherTemp");
    var label = document.getElementById("nvcWeatherLabel");
    var icon = document.getElementById("nvcWeatherIcon");
    var lat = Number(localStorage.getItem("NYXAL_WEATHER_LAT") || -23.5505);
    var lon = Number(localStorage.getItem("NYXAL_WEATHER_LON") || -46.6333);
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
      lat = -23.5505; lon = -46.6333;
    }
    var url = "https://api.open-meteo.com/v1/forecast?latitude=" + encodeURIComponent(lat) +
      "&longitude=" + encodeURIComponent(lon) +
      "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&timezone=auto";
    fetch(url, { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error("weather_http_" + response.status);
      return response.json();
    }).then(function (data) {
      var current = data.current || {};
      var code = Number(current.weather_code);
      var labels = {
        0: "céu limpo", 1: "quase limpo", 2: "parc. nublado", 3: "nublado",
        45: "neblina", 48: "neblina", 51: "garoa leve", 53: "garoa", 55: "garoa forte",
        61: "chuva leve", 63: "chuva", 65: "chuva forte", 71: "neve leve", 73: "neve", 75: "neve forte",
        80: "aguaceiros", 81: "aguaceiros", 82: "aguaceiros fortes", 95: "trovoada", 96: "trovoada", 99: "trovoada"
      };
      if (temp) temp.textContent = Number.isFinite(Number(current.temperature_2m)) ? Math.round(Number(current.temperature_2m)) + "°" : "--°";
      if (label) label.textContent = labels[code] || "condição atual";
      if (icon) icon.textContent = [0, 1].indexOf(code) >= 0 ? "☀" : ([2, 3].indexOf(code) >= 0 ? "☁" : "☂");
      var chip = label && label.closest(".nvc-chip");
      if (chip) chip.title = "Open-Meteo • umidade " + (current.relative_humidity_2m == null ? "—" : current.relative_humidity_2m + "%") + " • vento " + (current.wind_speed_10m == null ? "—" : current.wind_speed_10m + " km/h");
    }).catch(function () {
      if (temp) temp.textContent = "--°";
      if (label) label.textContent = "sem conexão";
      if (icon) icon.textContent = "◌";
    });
  }

  function loadReflectionState() {
    try {
      var raw = localStorage.getItem("NYXAL_REFLECTION_STATE");
      var value = raw ? JSON.parse(raw) : null;
      if (value && Number.isInteger(value.index) && Number.isFinite(value.at)) return value;
    } catch (_) {}
    return null;
  }

  function saveReflectionState(state) {
    try { localStorage.setItem("NYXAL_REFLECTION_STATE", JSON.stringify(state)); } catch (_) {}
  }

  function showInitialReflection() {
    var state = loadReflectionState();
    if (!state) {
      state = { index: Math.floor(Math.random() * reflections.length), at: Date.now() };
      saveReflectionState(state);
      renderReflection(state.index, true);
    } else {
      renderReflection(state.index, false);
      if (Date.now() - state.at >= REFLECTION_INTERVAL_MS) checkReflectionInterval();
    }
  }

  function checkReflectionInterval() {
    var state = loadReflectionState();
    if (!state) {
      showInitialReflection();
      return;
    }
    if (Date.now() - state.at < REFLECTION_INTERVAL_MS) return;
    rotateReflection(true);
  }

  function rotateReflection(showCard) {
    var state = loadReflectionState() || { index: -1, at: 0 };
    var next = (state.index + 1 + Math.floor(Math.random() * (reflections.length - 1))) % reflections.length;
    if (next === state.index) next = (next + 1) % reflections.length;
    state = { index: next, at: Date.now() };
    saveReflectionState(state);
    renderReflection(state.index, showCard);
  }

  function renderReflection(index, showCard) {
    var text = reflections[index] || reflections[0];
    var card = document.getElementById("nvcReflectionCard");
    var line = document.getElementById("nvcReflectionText");
    var full = document.getElementById("nvcReflectionFull");
    if (line) line.textContent = "“" + text + "”";
    if (full) full.textContent = "“" + text + "”";
    if (card && showCard) card.hidden = false;
  }

  function renderReflectionFull() {
    var state = loadReflectionState();
    renderReflection(state ? state.index : 0, false);
  }

  function speakCurrentReflection() {
    var state = loadReflectionState();
    var text = reflections[state ? state.index : 0];
    if (typeof window.speakGoddessNyxVoice === "function") {
      Promise.resolve(window.speakGoddessNyxVoice(text)).catch(function () {});
    } else {
      var synth = window.speechSynthesis;
      if (synth && window.SpeechSynthesisUtterance) {
        var utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "pt-BR";
        synth.speak(utterance);
      }
    }
  }

  function refreshVps() {
    var statusBox = document.getElementById("nvcVpsStatus");
    var list = document.getElementById("nvcVpsInstances");
    var message = document.getElementById("nvcVpsMessage");
    if (!statusBox || !list) return;
    statusBox.textContent = "Consultando hypervisor local…";
    list.replaceChildren();
    Promise.all([
      fetch(apiUrl("/api/vps/status"), { cache: "no-store" }).then(function (response) {
        if (!response.ok) throw new Error("vps_status_http_" + response.status);
        return response.json();
      }),
      fetch(apiUrl("/api/vps/instances"), { cache: "no-store" }).then(function (response) {
        if (!response.ok) throw new Error("vps_instances_http_" + response.status);
        return response.json();
      })
    ]).then(function (data) {
      var status = data[0] || {};
      var instances = data[1] || {};
      statusBox.textContent = status.operacional
        ? "HYPERVISOR ONLINE • " + String(status.backend || "libvirt/KVM") + " • domínios: " + String(status.dominios == null ? 0 : status.dominios)
        : "VPS indisponível • " + String(status.motivo || instances.motivo || "backend ainda não preparado");
      var rows = Array.isArray(instances.instancias) ? instances.instancias : [];
      if (!rows.length) {
        list.appendChild(element("div", "nvc-card nvc-muted", status.operacional ? "Nenhuma VPS encontrada." : "Instâncias não consultáveis neste momento."));
        return;
      }
      rows.forEach(function (item) {
        var card = element("div", "nvc-card");
        var row = element("div", "nvc-instance");
        var info = element("div", "");
        info.appendChild(element("strong", "", item.nome || "VPS"));
        info.appendChild(element("div", "nvc-status", String(item.estado || "estado desconhecido") + (Array.isArray(item.ips) && item.ips.length ? " • " + item.ips.join(", ") : "")));
        var actions = element("div", "nvc-instance-actions");
        [["start", "Ligar"], ["shutdown", "Desligar"], ["reboot", "Reiniciar"]].forEach(function (action) {
          var button = element("button", "nvc-button", action[1]);
          button.type = "button";
          button.addEventListener("click", function () { runVpsAction(String(item.nome || ""), action[0]); });
          actions.appendChild(button);
        });
        row.appendChild(info);
        row.appendChild(actions);
        card.appendChild(row);
        list.appendChild(card);
      });
    }).catch(function (error) {
      statusBox.textContent = "Não foi possível consultar o hypervisor. Verifique a API local e a configuração do libvirt.";
      if (message) message.textContent = String(error.message || error);
    });
  }

  function runVpsAction(name, action) {
    var message = document.getElementById("nvcVpsMessage");
    if (!name || ["start", "shutdown", "reboot"].indexOf(action) < 0) return;
    if (action !== "start" && !window.confirm("Confirma " + (action === "shutdown" ? "desligar" : "reiniciar") + " a VPS " + name + "?")) return;
    if (message) message.textContent = "Enviando ação explícita para " + name + "…";
    fetch(apiUrl("/api/vps/action"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: name, acao: action })
    }).then(function (response) {
      return response.json().then(function (payload) {
        if (!response.ok) throw new Error(payload.motivo || payload.estado || "Ação VPS recusada.");
        return payload;
      });
    }).then(function (payload) {
      if (message) message.textContent = String(payload.estado || payload.mensagem || "Ação enviada.") + " • atualizando estado…";
      window.setTimeout(refreshVps, 1200);
    }).catch(function (error) {
      if (message) message.textContent = "Ação não concluída: " + String(error.message || error);
    });
  }

  async function generateImage(promptOverride) {
    var promptField = document.getElementById("nvcImagePrompt");
    var status = document.getElementById("nvcImageStatus");
    var output = document.getElementById("nvcImageOutput");
    var prompt = String(promptOverride || (promptField && promptField.value) || "").trim();
    if (!prompt) {
      if (status) status.textContent = "Descreva a imagem antes de gerar.";
      return { sucesso: false, mensagem: "Descreva a imagem antes de gerar." };
    }
    if (prompt.length > 4000) {
      if (status) status.textContent = "A descrição ultrapassa o limite de 4.000 caracteres.";
      return { sucesso: false, mensagem: "A descrição ultrapassa 4.000 caracteres." };
    }
    if (promptField) promptField.value = prompt;
    var button = document.getElementById("nvcImageGenerate");
    if (button) button.disabled = true;
    if (status) status.textContent = "Solicitando geração visual ao provedor configurado…";
    if (output) output.replaceChildren();
    try {
      var response = await fetch(apiUrl("/api/agent/image"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt })
      });
      var payload = await response.json();
      if (!response.ok || payload.sucesso === false) {
        throw new Error(payload.motivo || payload.estado || "O provedor não gerou a imagem.");
      }
      if (!payload.imagem_base64 || !payload.mime_type) {
        throw new Error("A API respondeu sem dados de imagem.");
      }
      var img = document.createElement("img");
      img.alt = prompt;
      img.loading = "lazy";
      img.src = "data:" + payload.mime_type + ";base64," + payload.imagem_base64;
      if (output) output.appendChild(img);
      var actions = element("div", "nvc-row");
      var download = element("a", "nvc-button", "Salvar imagem");
      download.href = img.src;
      download.download = "nyxal-imagem-" + new Date().toISOString().replace(/[:.]/g, "-") + "." + (payload.mime_type.indexOf("jpeg") >= 0 ? "jpg" : payload.mime_type.indexOf("webp") >= 0 ? "webp" : "png");
      download.style.textDecoration = "none";
      actions.appendChild(download);
      if (output) output.appendChild(actions);
      var successMessage = String(payload.mensagem || "Imagem gerada.");
      if (Array.isArray(payload.avisos) && payload.avisos.length) {
        successMessage += " • " + payload.avisos.join(" • ");
      }
      if (status) status.textContent = successMessage;
      return { sucesso: true, mensagem: successMessage, payload: payload };
    } catch (error) {
      var errorMessage = "Geração indisponível: " + String(error.message || error) + " Confira a credencial do provedor visual e a conexão.";
      if (status) status.textContent = errorMessage;
      return { sucesso: false, mensagem: errorMessage };
    } finally {
      if (button) button.disabled = false;
    }
  }

  function extractConversationalImagePrompt(message) {
    var text = String(message || "").trim();
    var match = text.match(/^(?:(?:por favor|nyxal)[,;:\s!-]*)?(?:(?:gere|gera|gerar|crie|cria|criar|desenhe|desenha|desenhar|produza|produz|faça|faz)\s+|quero\s+(?:(?:criar|fazer|gerar)\s+)?|preciso\s+de\s+)(?:uma?\s+)?(?:imagem|ilustração|ilustracao|arte|figura|desenho|wallpaper|papel\s+de\s+parede|logo|logotipo|capa)\b(.*)$/i);
    if (!match) return null;
    var prompt = String(match[1] || "").replace(/^[\s:;,.-]*(?:(?:de|do|da|dos|das|sobre|com|mostrando|representando|para)\s+)?/i, "").trim();
    return prompt.length ? prompt : null;
  }

  window.nyxalHandleImageIntent = async function (message) {
    var prompt = extractConversationalImagePrompt(message);
    if (!prompt) return { handled: false };
    setView("image");
    setWorkspaceOpen(true);
    var result = await generateImage(prompt);
    var responseText = result.sucesso
      ? "A imagem está pronta no painel de ferramentas da Nyxal."
      : "Não consegui gerar a imagem. " + String(result.mensagem || "O provedor visual não retornou uma imagem.");
    return {
      handled: true,
      resposta: responseText,
      fala: result.sucesso ? "Pronto. Gerei a imagem e ela está visível no display." : responseText,
      sucesso: result.sucesso
    };
  };

  function handleKeyboard(event) {
    if (event.altKey && event.code === "Space") {
      event.preventDefault();
      toggleWorkspace();
      return;
    }
    if (!event.altKey || event.ctrlKey || event.metaKey) return;
    var target = event.target;
    if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
    var keyMap = { "1": "chat", "2": "vps", "3": "cyber", "4": "data", "5": "image", "6": "reflection" };
    var view = keyMap[event.key];
    if (!view) return;
    event.preventDefault();
    setView(view);
    setWorkspaceOpen(true);
  }

  function init() {
    if (ensureConsole()) {
      document.removeEventListener("keydown", handleKeyboard);
      document.addEventListener("keydown", handleKeyboard);
    }
  }

  if (document.readyState === "complete") window.setTimeout(init, 0);
  window.addEventListener("load", function () { window.setTimeout(init, 0); });
  if (document.body && window.MutationObserver) {
    var observer = new MutationObserver(function () {
      if (ensureConsole()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true });
  }

  window.addEventListener("nyxal:show-tools", function () {
    init();
    setWorkspaceOpen(true);
  });
})();