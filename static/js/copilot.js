// Copilot de Criação: UI + Lógica + Captura Semântica
(function(){
  // Gera um identificador único por sessão de aba para isolar o histórico por visitante
  const sesIdKey = 'copilotSessionId';
  let copilotSessionId = null;
  try {
    copilotSessionId = sessionStorage.getItem(sesIdKey);
  } catch(e) { copilotSessionId = null; }
  if (!copilotSessionId) {
    const genId = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : ('s' + Date.now() + Math.random().toString(16).slice(2));
    try { sessionStorage.setItem(sesIdKey, genId); } catch(e) {}
    copilotSessionId = genId;
  }
  const sesKey = 'copilotChatHistory:' + copilotSessionId;
  const elFab = document.getElementById('copilotFab');
  const elModal = document.getElementById('copilotModal');
  const elOverlay = elModal ? elModal.querySelector('.copilot-overlay') : null;
  const elPanel = elModal ? elModal.querySelector('.copilot-panel') : null;
  const elMin = elModal ? document.getElementById('copilotMinimize') : null;
  const elClose = elModal ? document.getElementById('copilotClose') : null;
  const elClear = elModal ? document.getElementById('copilotClear') : null;
  const elForm = elModal ? document.getElementById('copilotForm') : null;
  const elInput = elModal ? document.getElementById('copilotMessage') : null;
  const elSend = elForm ? elForm.querySelector('.copilot-send') : null;
  const elMsgs = elModal ? document.getElementById('copilotMessages') : null;
  const tplMsg = elModal ? document.getElementById('copilotMsgTemplate') : null;
  let isLoading = false;
  // Rastreamento de campos tocados pelo usuário
  const touched = new Set();

  // Util: persistência
  function loadHistory(){
    try {
      const raw = JSON.parse(sessionStorage.getItem(sesKey) || '[]');
      return Array.isArray(raw)
        ? raw.filter(m => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string' && m.content.trim().length > 0)
        : [];
    } catch(e){ return []; }
  }
  function saveHistory(hist){
    const clean = Array.isArray(hist)
      ? hist.filter(m => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string' && m.content.trim().length > 0)
      : [];
    sessionStorage.setItem(sesKey, JSON.stringify(clean));
  }

  // UI helpers
  function openModal(){ elModal.classList.add('open'); elModal.setAttribute('aria-hidden','false'); setTimeout(()=>{ elInput && elInput.focus(); }, 50); }
  function closeModal(){ elModal.classList.remove('open'); elModal.setAttribute('aria-hidden','true'); }
  function minimizeModal(){ closeModal(); }

  function renderMessage(role, content){
    if (!tplMsg || !elMsgs) return;
    const node = tplMsg.content.cloneNode(true);
    const wrap = node.querySelector('.copilot-msg');
    const bubble = node.querySelector('.copilot-bubble');
    wrap.classList.add(role);
    // Renderiza Markdown nas respostas da IA, texto puro para usuário
    if (role === 'assistant' && window.marked) {
      bubble.innerHTML = marked.parse(content || '');
    } else {
      bubble.textContent = content || '';
    }
    elMsgs.appendChild(node);
    // Mostrar início da resposta da IA, não o fim
    if (role === 'assistant') {
      elMsgs.scrollTop = wrap.offsetTop;
    } else {
      // Para mensagens do usuário, manter auto-scroll para o final
      elMsgs.scrollTop = elMsgs.scrollHeight;
    }
    return wrap;
  }

  function renderHistory(hist){
    if (!elMsgs) return;
    elMsgs.innerHTML = '';
    hist.forEach(m => renderMessage(m.role, m.content));
  }

  // Limpar histórico (frontend + chamada de backend)
  async function limparHistorico(){
    if (isLoading) {
      // Evita inconsistência: peça para aguardar término da resposta
      renderMessage('assistant', 'Aguarde a resposta terminar para limpar o histórico.');
      elMsgs.scrollTop = elMsgs.scrollHeight;
      return;
    }
    // Zera histórico no storage e na UI
    saveHistory([]);
    if (elMsgs) elMsgs.innerHTML = '';
    // Chama backend para limpar por sessão (no-op se não houver persistência)
    try {
      await fetch('/api/copilot/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: copilotSessionId })
      });
    } catch(e) { /* silencioso */ }
    // Reaplica saudação inicial
    const greet = 'Vou te orientar a preencher os campos para montar sua página. Me diga o que tem em mente!';
    const histNow = [{ role: 'assistant', content: greet }];
    saveHistory(histNow);
    renderMessage('assistant', greet);
    if (elInput) elInput.focus();
  }

  // Captura Semântica
  function capturarContextoConfirmado(){
    // Captura somente campos que o usuário tocou (confirmados), usando chaves baseadas em name/id/data-key
    const ctx = {};
    const form = document.getElementById('createForm');
    if (!form) return ctx;
    const fields = form.querySelectorAll('input, textarea, select');
    fields.forEach(el => {
      const key = el.name || el.id || el.getAttribute('data-key');
      if (!key) return;
      if (!touched.has(key)) return; // envia apenas campos tocados
      let val;
      if (el.type === 'checkbox') {
        val = !!el.checked;
      } else if (el.tagName.toLowerCase() === 'select') {
        val = el.value || (el.options && el.selectedIndex >= 0 ? el.options[el.selectedIndex].value : '');
      } else {
        val = el.value || '';
      }
      ctx[key] = val;
    });

    // Derivados: estado de fotos na UI (independente de toque)
    try {
      const carousel = document.getElementById('carousel');
      let photosCount = 0;
      if (carousel) {
        const imgs = carousel.querySelectorAll('.carousel-image');
        // Alinha com a lógica do frontend (script.js): conta imagens não-placeholder
        photosCount = Array.from(imgs).filter(img => {
          const src = (img.getAttribute('src') || '');
          return src.startsWith('data:') || !src.includes('placeholder_');
        }).length;
      }
      ctx['photos_count'] = photosCount;
      ctx['has_photos'] = photosCount > 0;
      // Texto visível "X/3 selecionadas" (se disponível)
      const infoEl = document.getElementById('photosLimitInfo');
      if (infoEl && typeof infoEl.textContent === 'string') {
        const m = infoEl.textContent.match(/(\d+)\/(\d+)/);
        if (m) {
          ctx['photos_selected_text'] = infoEl.textContent.trim();
          ctx['photos_selected'] = parseInt(m[1], 10);
          ctx['photos_max'] = parseInt(m[2], 10);
        }
      }
    } catch(e) { /* silencioso */ }

    // Derivados: estado de vídeo do YouTube na UI
    try {
      const ytInput = document.getElementById('youtubeLink');
      const rawUrl = ytInput ? (ytInput.value || '') : '';
      // Regex similar à lógica da prévia
      const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
      const match = rawUrl.match(regExp);
      const videoId = (match && match[2] && match[2].length === 11) ? match[2] : '';
      ctx['youtube_link_value'] = rawUrl;
      ctx['video_id'] = videoId;
      ctx['has_video'] = !!videoId;
    } catch(e) { /* silencioso */ }
    return ctx;
  }

  function capturarEstadoUI(){
    const state = {};
    const form = document.getElementById('createForm');
    if (!form) return state;
    const fields = form.querySelectorAll('input, textarea, select');
    fields.forEach(el => {
      const key = el.name || el.id || el.getAttribute('data-key') || el.placeholder || el.type || 'campo';
      let val;
      if (el.type === 'checkbox') {
        val = !!el.checked;
      } else if (el.tagName.toLowerCase() === 'select') {
        val = el.value || (el.options && el.selectedIndex >= 0 ? el.options[el.selectedIndex].value : '');
      } else {
        val = el.value || '';
      }
      state[key] = val;
    });
    return state;
  }

  async function enviarMensagem(texto){
    const histBefore = loadHistory();
    const form_context = capturarContextoConfirmado();
    const user_set_fields = Array.from(touched);
    // Constrói mapa de labels (nome semântico humano) por chave técnica
    function construirMapaLabels(){
      const map = {};
      const form = document.getElementById('createForm');
      if (!form) return map;
      const fields = form.querySelectorAll('input, textarea, select');
      fields.forEach(el => {
        const key = el.name || el.id || el.getAttribute('data-key');
        if (!key) return;
        let labelText = '';
        if (el.id) {
          const label = form.querySelector(`label[for="${CSS.escape(el.id)}"]`);
          if (label && label.textContent) labelText = label.textContent.trim();
        }
        if (!labelText) labelText = el.getAttribute('aria-label') || '';
        if (!labelText) labelText = el.placeholder || '';
        // Fallbacks por chave conhecida
        const nm = el.name || '';
        if (!labelText) {
          if (nm === 'name1') labelText = 'Nome 1';
          else if (nm === 'name2') labelText = 'Nome 2';
          else if (nm === 'event_date') labelText = 'Data do evento';
          else if (nm === 'event_time') labelText = 'Hora do evento';
          else if (nm === 'counter_mode') labelText = 'Tipo de contagem';
          else if (nm === 'event_description') labelText = 'Descrição do evento';
          else if (nm === 'custom_event_description') labelText = 'Frase personalizada';
          else if (nm === 'email') labelText = 'E-mail';
        }
        if (labelText) map[key] = labelText;
      });
      // Label combinado para descrição
      const l1 = map['event_description'];
      const l2 = map['custom_event_description'];
      map['event_description/custom_event_description'] = [l1, l2].filter(Boolean).join(' ou ') || 'Descrição do evento ou Frase personalizada';
      return map;
    }
    const label_map = construirMapaLabels();
    // Não adicionar chaves derivadas aos confirmados: apenas campos tocados são considerados confirmados
    const userMsg = { role: 'user', content: texto };
    const hist = Array.isArray(histBefore) ? histBefore.slice() : [];
    // Seleciona últimas N mensagens para contexto (antes da mensagem atual)
    const N = 20;
    const histForSend = (Array.isArray(histBefore) ? histBefore.slice(Math.max(0, histBefore.length - N)) : [])
      .filter(m => m && typeof m.content === 'string' && m.content.trim().length > 0 && (m.role === 'user' || m.role === 'assistant'));
    // Persiste e desenha a mensagem atual
    hist.push(userMsg); saveHistory(hist); renderMessage('user', texto);
    // Estado de carregamento: bloquear input e indicar pensamento
    isLoading = true;
    if (elInput) elInput.setAttribute('disabled', 'true');
    if (elSend) elSend.setAttribute('disabled', 'true');
    const thinkingText = 'A IA está pensando…';
    const placeholder = renderMessage('assistant', thinkingText);
    try {
      const resp = await fetch('/api/copilot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: texto,
          form_context,
          user_set_fields,
          label_map,
          history: histForSend,
          session_id: copilotSessionId
        })
      });
      const data = await resp.json();
      const ok = !!data.ok;
      const hasDetails = typeof data.details === 'string' && data.details.trim().length > 0;
      let reply = (typeof data.reply === 'string') ? data.reply : '';
      // Se houver erro, exibir mensagem de erro com detalhes e não mascarar com fallback
      if (!ok) {
        const err = (typeof data.error === 'string' && data.error.trim()) ? data.error : 'Erro desconhecido do provedor';
        reply = hasDetails ? `${err}\n\nDetalhes: ${data.details}` : err;
      }
      // Atualiza o placeholder com a resposta final ou remove se vazia
      if (placeholder) {
        const bubble = placeholder.querySelector('.copilot-bubble');
        if (!reply || !reply.trim()) {
          // Resposta vazia: remover placeholder e não persistir no histórico
          placeholder.remove();
        } else if (bubble) {
          if (window.marked) {
            bubble.innerHTML = marked.parse(reply);
          } else {
            bubble.textContent = reply;
          }
          // Garantir que a visualização fique no início da resposta
          elMsgs.scrollTop = placeholder.offsetTop;
        }
      }
      // Persiste no histórico somente se houver conteúdo
      if (reply && reply.trim()) {
        hist.push({ role: 'assistant', content: reply });
        saveHistory(hist);
      }
    } catch(e){
      const errText = `Falha ao contatar o backend: ${String(e)}`;
      // Atualiza o placeholder com erro
      if (placeholder) {
        const bubble = placeholder.querySelector('.copilot-bubble');
        if (bubble) bubble.textContent = errText;
      } else {
        renderMessage('assistant', errText);
      }
      hist.push({ role:'assistant', content: errText });
      saveHistory(hist);
    } finally {
      // Desbloqueia input e botão
      isLoading = false;
      if (elInput) elInput.removeAttribute('disabled');
      if (elSend) elSend.removeAttribute('disabled');
      if (elInput) elInput.focus();
    }
  }

  // Bindings
  if (elFab) elFab.addEventListener('click', openModal);
  if (elOverlay) elOverlay.addEventListener('click', minimizeModal);
  if (elMin) elMin.addEventListener('click', minimizeModal);
  if (elClose) elClose.addEventListener('click', closeModal);
  if (elClear) elClear.addEventListener('click', limparHistorico);
  if (elForm) elForm.addEventListener('submit', function(ev){
    ev.preventDefault();
    if (isLoading) return; // evita múltiplos envios enquanto carrega
    const txt = (elInput && elInput.value || '').trim();
    if (!txt) return;
    elInput.value = '';
    enviarMensagem(txt);
  });

  // Marca campos como tocados pelo usuário
  (function bindTouched(){
    const form = document.getElementById('createForm');
    if (!form) return;
    const fields = form.querySelectorAll('input, textarea, select');
    fields.forEach(el => {
      const key = el.name || el.id || el.getAttribute('data-key') || el.placeholder || el.type || 'campo';
      const markTouched = () => { if (key) touched.add(key); };
      el.addEventListener('input', markTouched);
      el.addEventListener('change', markTouched);
    });
  })();

  // Restaurar histórico ao carregar
  const initialHist = loadHistory();
  renderHistory(initialHist);

  // Padrão: manter o chat fechado ao carregar a página.
  // O usuário abre pelo botão flutuante (FAB).

  // Saudação inicial da IA só se o chat estiver vazio (primeira interação)
  if (!initialHist || initialHist.length === 0) {
    const greet = 'Vou te orientar a preencher os campos na tela. O que você quer homenagear?';
    const histNow = initialHist ? initialHist.slice() : [];
    histNow.push({ role: 'assistant', content: greet });
    saveHistory(histNow);
    renderMessage('assistant', greet);
  }
})();

// Exporta função para possível uso externo
window.capturarContextoSemantico = window.capturarContextoSemantico || (function(){
  const form = document.getElementById('createForm');
  if (!form) return function(){ return {}; };
  return function(){
    const ctx = {};
    const fields = form.querySelectorAll('input, textarea, select');
    function textoLabelPara(el){
      if (el.id) {
        const label = form.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (label && label.textContent) return label.textContent.trim();
      }
      if (el.placeholder && el.placeholder.trim()) return el.placeholder.trim();
      if (el.name && el.name.trim()) return el.name.trim();
      return (el.id || 'campo');
    }
    fields.forEach(el => {
      const key = textoLabelPara(el);
      let val;
      if (el.type === 'checkbox') {
        val = el.checked ? 'Marcado' : 'Desmarcado';
      } else if (el.tagName.toLowerCase() === 'select') {
        val = el.options && el.selectedIndex >= 0 ? el.options[el.selectedIndex].text : (el.value || '');
      } else {
        val = el.value || '';
      }
      ctx[key] = val;
    });
    return ctx;
  };
})();
