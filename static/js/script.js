$(document).ready(function () {
  /* =========================================
     GLOBAL VARIABLES & HELPER FUNCTIONS
     ========================================= */
  const $eventData = $("#event-data");
  const $counterContainer = $("#meu-contador");

  // Initial Data
  let eventDateStr = $eventData.data("event-date");
  let eventTimeStr = $eventData.data("event-time");
  let counterMode = $eventData.data("counter-mode") || "since";

  // Preview mode: when there is no real date/time provided in the page
  let isPreview = !eventDateStr;
  // Fixed example starting value (resets on page reload)
  const PREVIEW_FIXED = { days: 2, hours: 0, minutes: 0, seconds: 0 };
  let previewSecondsLeft = (
    (PREVIEW_FIXED.days || 0) * 24 * 3600 +
    (PREVIEW_FIXED.hours || 0) * 3600 +
    (PREVIEW_FIXED.minutes || 0) * 60 +
    (PREVIEW_FIXED.seconds || 0)
  );

  // If there is a real date, keep original behavior
  if (!isPreview) {
    let eventDate = new Date(`${eventDateStr}T${eventTimeStr || "00:00"}:00`);
    // Store globally for updateCounter
    window.__eventDate__ = eventDate;
  }


  function getManausTime() {
    let now = new Date();
    let options = {
      timeZone: "America/Manaus",
      year: "numeric", month: "numeric", day: "numeric",
      hour: "numeric", minute: "numeric", second: "numeric",
      hour12: false,
    };
    let formatter = new Intl.DateTimeFormat("en-US", options);
    let parts = formatter.formatToParts(now);

    let year = parts.find((p) => p.type === "year").value;
    let month = parts.find((p) => p.type === "month").value - 1;
    let day = parts.find((p) => p.type === "day").value;
    let hour = parts.find((p) => p.type === "hour").value;
    let minute = parts.find((p) => p.type === "minute").value;
    let second = parts.find((p) => p.type === "second").value;

    return new Date(year, month, day, hour, minute, second);
  }

  /* =========================================
     COUNTER LOGIC
     ========================================= */
  function updateCounter() {
    let finishedMsg = "";

    // Preview mode: always show a fixed starting value and decrement each second
    if (isPreview) {
      if (previewSecondsLeft < 0) previewSecondsLeft = 0;
      const seconds = previewSecondsLeft % 60;
      const minutesTotal = Math.floor(previewSecondsLeft / 60);
      const minutes = minutesTotal % 60;
      const hoursTotal = Math.floor(minutesTotal / 60);
      const hours = hoursTotal % 24;
      const days = Math.floor(hoursTotal / 24);

      const dYears = 0;
      const dMonths = 0;
      const dDays = days;
      const dHours = hours;
      const dMinutes = minutes;
      const dSeconds = seconds;

      // Helper to build HTML
      const buildBox = (val, label) => `
            <div class="time-box">
                <span class="time-value">${val}</span>
                <span class="time-label">${val === 1 ? label.slice(0, -1) : label}</span>
            </div>
        `;

      let html = "";
      if (dYears > 0) html += buildBox(dYears, "Anos");
      if (dMonths > 0 || dYears > 0) html += buildBox(dMonths, "Meses");
      html += buildBox(dDays, "Dias");
      html += buildBox(dHours, "Horas");
      html += buildBox(dMinutes, "Minutos");
      html += buildBox(dSeconds, "Segundos");

      $counterContainer.html(html);
      const $finish = $("#finish-message");
      if ($finish.length) $finish.html("");

      // Decrement after rendering (stops at zero)
      if (previewSecondsLeft > 0) previewSecondsLeft -= 1;
      return; // Do not run real counter logic
    }

    // Real date mode
    const currentDate = getManausTime();
    const eventDate = window.__eventDate__;
    let timeDiff;

    // Re-read mode from DOM in case it changed
    counterMode = $eventData.data("counter-mode") || "since";

    if (counterMode === "until") {
      timeDiff = eventDate.getTime() - currentDate.getTime();
    } else {
      timeDiff = currentDate.getTime() - eventDate.getTime();
    }

    // Countdown finished: show message with exact date/time and keep counter zeroed
    if (counterMode === "until" && timeDiff <= 0) {
      timeDiff = 0;
      const parts = new Intl.DateTimeFormat("pt-BR", {
        timeZone: "America/Manaus",
        day: "2-digit",
        month: "2-digit",
        year: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).formatToParts(eventDate);
      const getPart = (t) => (parts.find((p) => p.type === t) || {}).value || "";
      const whenStr = `${getPart("day")}/${getPart("month")}/${getPart("year")} às ${getPart("hour")}:${getPart("minute")}`;
      finishedMsg = `<div class="glass-card" style="padding: 1rem; margin-bottom: .5rem;"><h3 style="margin:0;">O evento chegou em ${whenStr}</h3></div>`;
    }

    if (timeDiff < 0) timeDiff = Math.abs(timeDiff);

    const seconds = Math.floor(timeDiff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    const months = Math.floor(days / 30);
    const years = Math.floor(months / 12);

    const dYears = years;
    const dMonths = months % 12;
    const dDays = days % 30;
    const dHours = hours % 24;
    const dMinutes = minutes % 60;
    const dSeconds = seconds % 60;

    // Helper to build HTML
    const buildBox = (val, label) => `
            <div class="time-box">
                <span class="time-value">${val}</span>
                <span class="time-label">${val === 1 ? label.slice(0, -1) : label}</span>
            </div>
        `;

    let html = "";
    if (dYears > 0) html += buildBox(dYears, "Anos");
    if (dMonths > 0 || dYears > 0) html += buildBox(dMonths, "Meses");
    html += buildBox(dDays, "Dias");
    html += buildBox(dHours, "Horas");
    html += buildBox(dMinutes, "Minutos");
    html += buildBox(dSeconds, "Segundos");

    // Render only the counter boxes
    $counterContainer.html(html);
    // Place the finish message at the end (after description), if present
    const $finish = $("#finish-message");
    if ($finish.length) {
      $finish.html(finishedMsg);
    }
  }

  // Atualiza prévia da data selecionada em formato brasileiro
  function updateSelectedDateHint() {
    const d = $("#event_date").val();
    const t = $("#event_time").val();
    const $hint = $("#eventDateHint");
    if (!$hint.length) return;
    if (!d) {
      $hint.text("Formato: dia/mês/ano");
      return;
    }
    try {
      const dt = new Date(`${d}T${t || "00:00"}:00`);
      const parts = new Intl.DateTimeFormat("pt-BR", {
        timeZone: "America/Manaus",
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).formatToParts(dt);
      const get = (k) => (parts.find((p) => p.type === k) || {}).value || "";
      const dateStr = `${get("day")}/${get("month")}/${get("year")}`;
      const timeStr = t ? `${get("hour")}:${get("minute")}` : "";
      $hint.text(timeStr ? `Selecionado: ${dateStr} às ${timeStr}` : `Selecionado: ${dateStr}`);
    } catch (e) {
      $hint.text("Selecionado: "+ d);
    }
  }

  // Atualiza o card de validade com a data/hora atual em pt-BR
  function updateActiveUntilNow() {
    const $val = $("#activeUntilValue");
    if (!$val.length) return;
    try {
      const now = new Date();
      const parts = new Intl.DateTimeFormat("pt-BR", {
        timeZone: "America/Manaus",
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).formatToParts(now);
      const get = (k) => (parts.find((p) => p.type === k) || {}).value || "";
      const dateStr = `${get("day")}/${get("month")}/${get("year")}`;
      const timeStr = `${get("hour")}:${get("minute")}`;
      $val.text(`${dateStr} ${timeStr}`);
    } catch (e) {
      $val.text("--/--/---- --:--");
    }
  }

  // Start Timer
  setInterval(updateCounter, 1000);
  updateCounter();

  /* =========================================
     CAROUSEL LOGIC
     ========================================= */
  // Ajustes de imagem (zoom/rotação) por índice do carrossel
  let currentAdjustments = {};

  // Inicializa ajustes vindos do backend (couple_page) e normaliza chaves
  (function initAdjustmentsFromHidden() {
    try {
      const el = document.getElementById('imageAdjustmentsData');
      if (!el) return;
      const raw = JSON.parse(el.value || '{}');
      const norm = {};
      Object.keys(raw || {}).forEach((k) => {
        const idx = parseInt(k, 10);
        norm[isNaN(idx) ? k : idx] = raw[k];
      });
      currentAdjustments = norm;
    } catch (e) {
      console.warn('[initAdjustmentsFromHidden] falha ao carregar ajustes:', e);
    }
  })();
  let carouselInterval;
  function startCarousel() {
    if (carouselInterval) clearInterval(carouselInterval);

    const advance = () => {
      const $images = $(".carousel-image");
      if ($images.length <= 1) return;
      const $active = $images.filter(".active");
      const currentIdx = $images.index($active);
      const nextIdx = (currentIdx + 1) % $images.length;
      setActiveIndex(nextIdx, 'forward');
    };

    // Intervalo definido para 4 segundos por slide
    carouselInterval = setInterval(advance, 4000);
  }

  startCarousel();

  // Helpers de navegação do carrossel
  // Usa variáveis CSS para compor transform: user-ajuste + slideX
  function applyAdjustmentVars(i, $el) {
    const adj = (currentAdjustments && currentAdjustments[i]) || { x: 0, y: 0, scale: 1, rotate: 0 };
    const rot = typeof adj.rotate === 'number' ? adj.rotate : 0;
    $el.css({
      '--tx': `${adj.x}px`,
      '--ty': `${adj.y}px`,
      '--scale': adj.scale,
      '--rot': `${rot}deg`
    });
  }
  let isAnimating = false;
  function setActiveIndex(idx, direction) {
    const $images = $(".carousel-image");
    if ($images.length === 0 || isAnimating) return;
    idx = Math.max(0, Math.min(idx, $images.length - 1));
    const $current = $images.filter('.active');
    const currentIdx = $images.index($current);
    const currentDataIdx = ($current.data('index') !== undefined) ? $current.data('index') : currentIdx;
    if (currentIdx === idx) return;
    const $next = $images.eq(idx);
    const nextDataIdx = ($next.data('index') !== undefined) ? $next.data('index') : idx;

    // Efeito apenas fade (sem slide)
    isAnimating = true;

    // Preparação de estados
    $images.css({ zIndex: 0 });
    applyAdjustmentVars(currentDataIdx, $current);
    applyAdjustmentVars(nextDataIdx, $next);
    $current.css({ opacity: 1, zIndex: 1 });
    $next.css({ opacity: 0, zIndex: 2 });
    $next.addClass('active');

    // Força reflow antes de animar
    void $next[0].offsetWidth;

    // Anima somente opacidade
    $current.css({ opacity: 0 });
    $next.css({ opacity: 1 });

    setTimeout(() => {
      // Finaliza estados
      $images.each(function(i){
        if (i !== idx) {
          const di = ($(this).data('index') !== undefined) ? $(this).data('index') : i;
          const $el = $(this);
          applyAdjustmentVars(di, $el);
          $el.removeClass('active').css({ opacity: 0, zIndex: 0 });
        }
      });
      try { activeImageIndex = idx; } catch(e) {}
      updateCarouselDots();
      updateCarouselControlsVisibility();
      isAnimating = false;
    }, 520); // ~0.5s + pequena margem
  }

  function nextImage() {
    const $images = $(".carousel-image");
    if ($images.length <= 1) return;
    const currentIdx = $images.index($images.filter('.active'));
    setActiveIndex((currentIdx + 1) % $images.length, 'forward');
    startCarousel();
  }

  function prevImage() {
    const $images = $(".carousel-image");
    if ($images.length <= 1) return;
    const currentIdx = $images.index($images.filter('.active'));
    setActiveIndex((currentIdx - 1 + $images.length) % $images.length, 'backward');
    startCarousel();
  }

  function rebuildCarouselDots() {
    const $dots = $("#carouselDots");
    if ($dots.length === 0) return;
    const $images = $(".carousel-image");
    $dots.empty();
    $images.each(function(i){
      const $d = $('<span class="dot" data-idx="'+i+'" style="width:10px;height:10px;border-radius:50%;background: currentColor; opacity: .35; display:inline-block; cursor:pointer;"></span>');
      $d.on('click', function(){
        const currentIdx = $(".carousel-image").index($(".carousel-image.active"));
        const dir = i > currentIdx ? 'forward' : 'backward';
        setActiveIndex(i, dir); startCarousel();
      });
      $dots.append($d);
    });
    updateCarouselDots();
  }

  function updateCarouselDots() {
    const $dots = $("#carouselDots .dot");
    if ($dots.length === 0) return;
    const currentIdx = $(".carousel-image").index($(".carousel-image.active"));
    $dots.css({ background: 'currentColor', opacity: .35 });
    $dots.eq(currentIdx).css({ background: 'currentColor', opacity: 1 });
  }

  // Eventos de botões
  $(document).on('click', '#nextPhotoBtn', nextImage);
  $(document).on('click', '#prevPhotoBtn', prevImage);

  // Oculta/mostra controles conforme quantidade de fotos
  function updateCarouselControlsVisibility() {
    const count = $(".carousel-image").length;
    const $controls = $("#carouselControls");
    if (!$controls.length) return;
    if (count <= 1) {
      $controls.css('opacity', .6);
      $("#prevPhotoBtn, #nextPhotoBtn").attr('disabled', true).css('pointer-events','none');
    } else {
      $controls.css('opacity', 1);
      $("#prevPhotoBtn, #nextPhotoBtn").attr('disabled', false).css('pointer-events','auto');
    }
  }

  // Swipe em mobile para navegar no carrossel
  (function initCarouselSwipe(){
    let touchStartX = null;
    let touchEndX = null;
    const threshold = 30; // px
    $(document).on('touchstart', '#carousel', function(e){
      if (!e.originalEvent || !e.originalEvent.touches || e.originalEvent.touches.length === 0) return;
      touchStartX = e.originalEvent.touches[0].clientX;
    });
    $(document).on('touchend', '#carousel', function(e){
      const t = e.originalEvent && e.originalEvent.changedTouches && e.originalEvent.changedTouches[0];
      if (!t || touchStartX === null) return;
      touchEndX = t.clientX;
      const dx = touchEndX - touchStartX;
      if (Math.abs(dx) > threshold) { dx < 0 ? nextImage() : prevImage(); }
      touchStartX = null; touchEndX = null;
    });
  })();

  // Teclado: setas para navegar e Delete para excluir (na prévia)
  $(document).on('keydown', '#carousel', function(e){
    if (e.key === 'ArrowLeft') { e.preventDefault(); prevImage(); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); nextImage(); }
    else if (e.key === 'Delete') { $("#deletePhotoBtn").trigger('click'); }
  });

  // Excluir foto ativa na prévia (index)
  $(document).on('click', '#deletePhotoBtn', function(){
    const $carousel = $('#carousel');
    const $images = $carousel.find('.carousel-image');
    if ($images.length === 0) return;
    const $active = $carousel.find('.carousel-image.active');
    if ($active.length === 0) return;
    const currentIdx = $images.index($active);

    // Remove do buffer de arquivos
    const imagesInput = document.getElementById('images');
    const isPlaceholder = (($active.attr('src') || '').includes('placeholder_'));
    if (!isPlaceholder) {
      const $userImages = $carousel.find('.carousel-image[data-index]');
      const userIdx = $userImages.index($active);
      const hasDT = (typeof imagesDT !== 'undefined') && imagesDT && imagesDT.files && imagesDT.files.length > 0;
      const hasAcc = (typeof accumulatedFiles !== 'undefined') && Array.isArray(accumulatedFiles) && accumulatedFiles.length > 0;
      if (hasDT) {
        const newDT = new DataTransfer();
        Array.from(imagesDT.files).forEach((file,i) => { if (i !== userIdx) newDT.items.add(file); });
        imagesDT = newDT;
        if (imagesInput) imagesInput.files = imagesDT.files;
      } else if (hasAcc) {
        accumulatedFiles.splice(userIdx, 1);
      }
    }

    // Remove do DOM e reindexa
    $active.remove();
    const $remaining = $carousel.find('.carousel-image');
    // Reindexa somente fotos do usuário (não define data-index no placeholder)
    $remaining.filter('[data-index]').each(function(i){ $(this).attr('data-index', i); });
    if ($remaining.length === 0) {
      addDefaultPlaceholders($carousel);
    } else {
      setActiveIndex(Math.max(0, currentIdx - 1));
    }

    rebuildCarouselDots();
    updateCarouselControlsVisibility();
    const hasDTCount = (typeof imagesDT !== 'undefined') && imagesDT && imagesDT.files;
    const hasAccCount = (typeof accumulatedFiles !== 'undefined') && Array.isArray(accumulatedFiles);
    const totalBuffered = hasDTCount ? imagesDT.files.length : (hasAccCount ? accumulatedFiles.length : 0);
    updatePhotosCountInfo(totalBuffered, 3);
    updateEditButtonVisibility();
    updateDeleteButtonVisibility();
  });

  /* =========================================
     AMBIENT PARTICLES GENERATOR
     ========================================= */
  (function generateAmbientParticles() {
    const $ambient = $("#ambientParticles");
    if (!$ambient.length) return;
    const count = 24;
    for (let i = 0; i < count; i++) {
      const size = 4 + Math.floor(Math.random() * 10); // 4..14px
      const x = Math.floor(Math.random() * 100); // percent
      const y = Math.floor(Math.random() * 100); // percent
      const tx = (Math.random() * 200 - 100).toFixed(0); // -100..100px
      const ty = (Math.random() * 200 - 100).toFixed(0); // -100..100px
      const dur = 14 + Math.floor(Math.random() * 10); // 14..24s
      const delay = -Math.floor(Math.random() * dur);

      const $p = $('<span class="particle"></span>');
      $p.css({
        width: size + "px",
        height: size + "px",
        left: x + "%",
        top: y + "%",
        "--tx": tx + "px",
        "--ty": ty + "px",
        animationDuration: dur + "s",
        animationDelay: delay + "s",
      });
      $ambient.append($p);
    }
  })();

  /* =========================================
     EFFECTS LOGIC
     ========================================= */
  const $effectContainer = $("#presentationEffectContainer");
  let effectInterval;

  function createIcon(type) {
    const symbols = { hearts: "❤️", stars: "⭐", confetti: "🎉" };
    const icon = $(`<div class="floating-icon">${symbols[type] || "❤️"}</div>`);

    icon.css({
      position: "absolute",
      left: Math.random() * 100 + "%",
      top: "100%",
      fontSize: (Math.random() * 20 + 16) + "px",
      opacity: Math.random() * 0.5 + 0.5,
      color: "white",
      transition: `top ${Math.random() * 2 + 3}s linear, opacity 3s ease-out`
    });

    $effectContainer.append(icon);

    setTimeout(() => {
      icon.css({ top: "-20%", opacity: 0 });
    }, 50);

    setTimeout(() => icon.remove(), 4000);
  }

  function startEffects() {
    if (effectInterval) clearInterval(effectInterval);

    const type = $("#imageEffectSelector").val() || $("#imageEffectSelector").attr("value");
    if (!type || type === "none") {
      // Limpa quaisquer ícones existentes e evita continuar gerando
      if ($effectContainer && $effectContainer.length) {
        $effectContainer.empty();
      }
      return;
    }

    effectInterval = setInterval(() => {
      createIcon(type);
    }, 500);
  }

  $("#imageEffectSelector").on("change", startEffects);
  startEffects();

  /* =========================================
     PREVIEW LOGIC (Index Page Only)
     ========================================= */
  if ($("#createForm").length) {
    // Alternância de abas (Prévia / Crie a sua)
    (function initTabs(){
      const $btnPrev = $("#tabBtnPreview");
      const $btnCreate = $("#tabBtnCreate");
      const $panelPrev = $("#previewPanel");
      const $panelCreate = $("#createPanel");
      if (!$btnPrev.length || !$btnCreate.length || !$panelPrev.length || !$panelCreate.length) return;

      function activate(tab){
        const isPrev = tab === "preview";
        $btnPrev.toggleClass("active", isPrev);
        $btnCreate.toggleClass("active", !isPrev);
        $panelPrev.toggleClass("active", isPrev);
        $panelCreate.toggleClass("active", !isPrev);
        if (isPrev) {
          updateSelectedDateHint();
          updateActiveUntilNow();
          updateCounter();
        }
      }

      $btnPrev.on("click", () => activate("preview"));
      $btnCreate.on("click", () => activate("create"));
      // Estado inicial: prévia ativa
      activate("preview");
    })();
    // Update Date/Time
    $("#event_date, #event_time").on("change", function () {
      const d = $("#event_date").val();
      const t = $("#event_time").val();
      if (d && t) {
        eventDate = new Date(`${d}T${t}:00`);
        window.__eventDate__ = eventDate;
        isPreview = false;
        updateCounter();
      }
      updateSelectedDateHint();
    });

    // Inicializa card de validade com a data/hora atual e atualiza a cada minuto
    updateActiveUntilNow();
    setInterval(updateActiveUntilNow, 60 * 1000);

    // Update Names
    $("#name1, #name2").on("input", function () {
      const n1 = $("#name1").val().trim();
      const n2 = $("#name2").val().trim();

      if (!n1 && !n2) {
        $("#couple_name1").text("Ana");
        $("#couple_name2").text("João").show();
        $("#e_comercial").show();
        return;
      }

      if (n1) {
        $("#couple_name1").text(n1);
      } else {
        $("#couple_name1").text("");
      }

      if (n2) {
        $("#couple_name2").text(n2).show();
        $("#e_comercial").show();
      } else {
        $("#couple_name2").hide();
        $("#e_comercial").hide();
      }
    });

    // Inicializa nomes padrão apenas na PRÉVIA (inputs vazios)
    (function initNamesDefaults(){
      const n1 = $("#name1").val().trim();
      const n2 = $("#name2").val().trim();
      if (!n1 && !n2) {
        $("#couple_name1").text("Ana");
        $("#couple_name2").text("João").show();
        $("#e_comercial").show();
      } else {
        $("#name1, #name2").trigger("input");
      }
    })();

    // Event Options
    const eventOptions = {
      since: {
        "Relacionamentos amorosos 💑": [
          { value: "se casaram", singular: "se casou", plural: "se casaram" },
          { value: "se conheceram", singular: "conheceu alguém especial", plural: "se conheceram" },
          { value: "começaram a namorar", singular: "começou a namorar", plural: "começaram a namorar" },
          { value: "noivaram", singular: "noivou", plural: "noivaram" },
          { value: "deram o primeiro beijo", singular: "deu o primeiro beijo", plural: "deram o primeiro beijo" },
          { value: "foram morar juntos", singular: "foi morar junto", plural: "foram morar juntos" }
        ],
        "Família e Amigos 👨‍👩‍👧‍👦": [
          { value: "se tornaram amigos", singular: "fez um novo amigo", plural: "se tornaram amigos" },
          { value: "se reencontraram", singular: "reencontrou alguém", plural: "se reencontraram" },
          { value: "a família aumentou", singular: "a família aumentou", plural: "a família aumentou" }
        ],
        "Conquistas Pessoais 🏆": [
          { value: "nasceu", singular: "nasceu", plural: "nasceram" },
          { value: "se formou", singular: "se formou", plural: "se formaram" },
          { value: "começou no novo emprego", singular: "começou no novo emprego", plural: "começaram no novo emprego" },
          { value: "realizou um sonho", singular: "realizou um sonho", plural: "realizaram um sonho" },
          { value: "mudou de cidade", singular: "mudou de cidade", plural: "mudaram de cidade" }
        ]
      },
      until: {
        "Relacionamentos amorosos \ud83d\udc91": [
          { value: "se casarem", singular: "se casar", plural: "se casarem" },
          { value: "noivarem", singular: "noivar", plural: "noivarem" },
          { value: "morarem juntos", singular: "morar junto", plural: "morarem juntos" },
          { value: "a lua de mel", singular: "a lua de mel", plural: "a lua de mel" },
          { value: "renovarem os votos", singular: "renovar os votos", plural: "renovarem os votos" }
        ],
        "Fam\u00edlia e Amigos \ud83d\udc68\ud83d\udc69\ud83d\udc67\ud83d\udc66": [
          { value: "se reencontrarem", singular: "se reencontrar", plural: "se reencontrarem" },
          { value: "o nascimento do beb\u00ea", singular: "o nascimento do beb\u00ea", plural: "o nascimento do beb\u00ea" },
          { value: "a festa de 15 anos", singular: "a festa de 15 anos", plural: "a festa de 15 anos" }
        ],
        "Conquistas e Planos \ud83d\ude80": [
          { value: "a formatura", singular: "a formatura", plural: "a formatura" },
          { value: "a viagem dos sonhos", singular: "a viagem dos sonhos", plural: "a viagem dos sonhos" },
          { value: "a aposentadoria", singular: "a aposentadoria", plural: "a aposentadoria" },
          { value: "a mudan\u00e7a de casa", singular: "a mudan\u00e7a de casa", plural: "a mudan\u00e7a de casa" },
          { value: "realizar um sonho", singular: "realizar um sonho", plural: "realizarem um sonho" }
        ],
        "Celebra\u00e7\u00f5es \ud83c\udf82": [
          { value: "o anivers\u00e1rio", singular: "o anivers\u00e1rio", plural: "o anivers\u00e1rio" }
        ]
      }
    };

    function updateEventSelectOptions(mode) {
      const $select = $("#eventSelect");
      const currentVal = $select.val();
      // Considera plural quando houver segundo nome no input OU o segundo nome estiver visível na prévia
      const hasSecondName = $("#name2").val().trim().length > 0 || $("#couple_name2").is(":visible");
      $select.empty();

      const groups = eventOptions[mode];
      if (groups) {
        for (const [groupLabel, options] of Object.entries(groups)) {
          const $optgroup = $("<optgroup>").attr("label", groupLabel);
          options.forEach(opt => {
            const text = hasSecondName ? opt.plural : opt.singular;
            $("<option>").val(opt.value).text(text).appendTo($optgroup);
          });
          $select.append($optgroup);
        }
      }

      if (currentVal) {
        $select.val(currentVal);
      }

      // Se nada estiver selecionado após repovoar, define a primeira opção
      if (!$select.val()) {
        const firstOpt = $select.find("option").first();
        if (firstOpt.length) {
          $select.val(firstOpt.val());
        }
      }
    }

    function updateDescriptionAndMode() {
      const mode = $("input[name='counter_mode']:checked").val();
      const useCustom = $("#customPhraseToggle").is(":checked");
      const customText = $("#customPhraseInput").val();
      // Para refletir corretamente singular/plural, usamos o texto da opção selecionada
      const selectText = $("#eventSelect option:selected").text();

      $eventData.data("counter-mode", mode);
      $("#counter_prefix_text").text(mode === "until" ? "Faltam:" : "Já se passaram:");

      const prefix = mode === "until" ? "para " : "desde que ";
      let mainText = useCustom && customText ? customText : selectText;
      // Fallback: se a seleção estiver vazia após trocar modo, usa a primeira opção
      if (!mainText) {
        const firstOpt = $("#eventSelect option").first();
        if (firstOpt.length) {
          $("#eventSelect").val(firstOpt.val());
          mainText = firstOpt.text();
        } else {
          mainText = "o evento escolhido"; // fallback genérico
        }
      }
      $("#event_description_text").text(prefix + mainText);

      if (useCustom) {
        $("#customPhraseInput").removeClass("d-none");
        $("#eventSelect").addClass("d-none");
        $("#descriptionMode").val("custom").trigger("input");
      } else {
        $("#customPhraseInput").addClass("d-none");
        $("#eventSelect").removeClass("d-none");
        $("#descriptionMode").val("select").trigger("input");
      }

      updateCounter();
    }

    $("input[name='counter_mode']").on("change", function () {
      const mode = $(this).val();
      updateEventSelectOptions(mode);
      updateDescriptionAndMode();
    });

    $("#name2").on("input", function () {
      const mode = $("input[name='counter_mode']:checked").val();
      updateEventSelectOptions(mode);
      updateDescriptionAndMode();
    });

    $("#customPhraseToggle, #eventSelect, #customPhraseInput").on("change input", updateDescriptionAndMode);

    function escapeHtml(str) {
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }
    function isEmojiChar(ch) {
      const cp = ch.codePointAt(0);
      return (
        (cp >= 0x1F300 && cp <= 0x1FAFF) || // emojis principais
        (cp >= 0x2600 && cp <= 0x27BF) ||   // símbolos diversos
        cp === 0x2764 ||                    // ❤
        cp === 0x1F970 ||                   // 🥰
        cp === 0x1F48D ||                   // 💍
        cp === 0x1F4F8 ||                   // 📸
        cp === 0x1F3B5 ||                   // 🎵
        cp === 0x2600                       // ☀
      );
    }
    function renderMessageWithEmojiIsolation(text) {
      let out = "";
      let buffer = "";
      for (const ch of text || "") {
        if (isEmojiChar(ch)) {
          if (buffer) {
            out += `<span class="themed-text special-text">${escapeHtml(buffer)}</span>`;
            buffer = "";
          }
          out += `<span class="emoji">${escapeHtml(ch)}</span>`;
        } else {
          buffer += ch;
        }
      }
      if (buffer) {
        out += `<span class="themed-text special-text">${escapeHtml(buffer)}</span>`;
      }
      return out || `<span class="themed-text special-text">Sua mensagem aparecerá aqui...</span>`;
    }
    $("#message").on("input", function () {
      const msg = $(this).val();
      const html = renderMessageWithEmojiIsolation(msg);
      $("#optional_message_text").html(html);
    });

    // Inicializa descrição com base no modo atual e primeira opção
(function initDescription() {
  const initMode = $("input[name='counter_mode']:checked").val();
  updateEventSelectOptions(initMode);
  updateDescriptionAndMode();
})();

    // Date Picker (Flatpickr) - mostra dd/mm/aaaa, envia Y-m-d
    document.addEventListener('DOMContentLoaded', function () {
      try {
        if (window.flatpickr && document.querySelector('#event_date')) {
          flatpickr('#event_date', {
            dateFormat: 'Y-m-d',       // valor real enviado ao backend
            altInput: true,            // mostra um input amigável
            altFormat: 'd/m/Y',        // formato brasileiro visível
            allowInput: true,
            locale: (window.flatpickr?.l10ns?.pt) || 'pt'
          });
        }
      } catch (e) {
        console.warn('Falha ao inicializar Flatpickr:', e);
      }
    });

    // Photo Adjustment
    // Buffer de arquivos para acumular seleções múltiplas do input
    var imagesDT;
    try {
      imagesDT = new DataTransfer();
    } catch (e) {
      imagesDT = null; // fallback para navegadores sem DataTransfer
    }
    var accumulatedFiles = [];
    let isDragging = false;
    let startX, startY, currentX = 0, currentY = 0, currentScale = 1, currentRotation = 0;
    let activeImageIndex = 0;

    function addDefaultPlaceholders($carousel) {
      const placeholderSrcs = [
        '/static/images/placeholder_1.png',
        '/static/images/placeholder_2.png',
        '/static/images/placeholder_3.png',
      ];
      // Remove quaisquer existentes antes de adicionar novamente
      $carousel.find('.carousel-image').remove();
      placeholderSrcs.forEach((src, idx) => {
        const activeClass = idx === 0 ? ' active' : '';
        const opacity = idx === 0 ? 1 : 0;
    $carousel.append(`<img src="${src}" class="carousel-image${activeClass}" data-index="${idx}" style="width: 100%; height: 100%; object-fit: contain; position: absolute; top: 0; left: 0; opacity: ${opacity}; transform: translate(var(--tx, 0px), var(--ty, 0px)) scale(var(--scale, 1)) rotate(var(--rot, 0deg)); transition: transform 0.6s ease, opacity 0.6s ease; will-change: transform, opacity;">`);
      });
      // Inicializa variáveis padrões para todos
    $carousel.find('.carousel-image').each(function(i){ applyAdjustmentVars(i, $(this)); });
      setActiveIndex(0);
      rebuildCarouselDots();
      updateCarouselControlsVisibility();
      updateEditButtonVisibility();
    }

    function hasUserPhotos() {
      const $userImgs = $('#carousel .carousel-image[data-index]');
      return $userImgs.length > 0;
    }

    function updateEditButtonVisibility() {
      if (hasUserPhotos()) {
        $("#editPhotoBtn").fadeIn();
      } else {
        $("#editPhotoBtn").hide();
      }
    }

    $("#images").on("change", function () {
      const inputEl = this;
      const incomingFiles = Array.from(inputEl.files || []);
      const $carousel = $("#carousel");

      // Remove somente placeholder, preservando imagens já adicionadas
      $carousel
        .find(".carousel-image")
        .filter(function () {
          const src = $(this).attr("src") || "";
          return src.includes("placeholder_");
        })
        .remove();

      const existingCount = $carousel.find(".carousel-image").length;

      // Adiciona os novos arquivos ao buffer acumulado (máximo 3), evitando duplicados
      const maxPhotos = 3;
      const filesToAppend = [];
      let ignoredCount = 0;
      incomingFiles.forEach((file) => {
        if (accumulatedFiles.length >= maxPhotos) { ignoredCount++; return; }
        const isDupAcc = accumulatedFiles.some(
          (f) => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified
        );
        if (isDupAcc) return;
        accumulatedFiles.push(file);
        filesToAppend.push(file);
      });

      // Se possível, espelha o buffer acumulado em DataTransfer para atualizar o input.files
      const imagesInput = document.getElementById("images");
      if (imagesInput && imagesDT) {
        try {
          const dt = new DataTransfer();
          accumulatedFiles.slice(0, maxPhotos).forEach((f)=> dt.items.add(f));
          imagesDT = dt;
          imagesInput.files = imagesDT.files;
        } catch (e) {
          // Fallback: se falhar, mantém apenas accumulatedFiles para envio via FormData
          console.warn('[images change] DataTransfer add falhou, usando accumulatedFiles apenas');
        }
      }

      const totalBuffered = accumulatedFiles.length;
      // Atualiza contador visual (se existir)
      updatePhotosCountInfo(totalBuffered, maxPhotos);
      if (ignoredCount > 0) {
        if (window.Swal) {
          Swal.fire({ icon: 'info', title: 'Limite de fotos', text: 'Você pode enviar até 3 fotos. Remova alguma para adicionar outra.' });
        }
      }
      if (totalBuffered === 0 && existingCount === 0) {
        addDefaultPlaceholders($carousel);
        return;
      }

      let loadedCount = 0;
      const totalFiles = filesToAppend.length;

      filesToAppend.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = function (e) {
          // Define índice acumulado e ativa apenas se ainda não houver imagem ativa
          const dataIndex = existingCount + index;
          const hasActive = $carousel.find(".carousel-image.active").length > 0;
          const activeClass = (!hasActive && index === 0) ? "active" : "";
          const initialOpacity = activeClass ? 1 : 0;
    const img = $(`<img src="${e.target.result}" class="carousel-image ${activeClass}" data-index="${dataIndex}" style="width: 100%; height: 100%; object-fit: contain; position: absolute; top: 0; left: 0; opacity: ${initialOpacity}; transform: translate(var(--tx, 0px), var(--ty, 0px)) scale(var(--scale, 1)) rotate(var(--rot, 0deg)); transition: transform 0.6s ease, opacity 0.6s ease; will-change: transform, opacity;">`);
          $carousel.append(img);
          applyAdjustmentVars(dataIndex, img);
    // fade-only: sem slideX

          loadedCount++;
          if (loadedCount === totalFiles) {
            // Atualiza campo oculto com ajustes atuais (preservados)
            $("#imageAdjustments").val(JSON.stringify(currentAdjustments));
            startCarousel();
            rebuildCarouselDots();
            updateEditButtonVisibility();
            updateDeleteButtonVisibility();
            updateCarouselControlsVisibility();
          }
        };
        reader.readAsDataURL(file);
      });

      // Limpa valor do input para permitir adicionar novamente o mesmo arquivo se desejado
      // Somente se DataTransfer existir; caso contrário, manter os arquivos no input
      if (imagesDT) {
        inputEl.value = "";
      }
      try {
        console.log('[images change] buffered=', accumulatedFiles.length,
          'DT=', imagesDT ? imagesDT.files.length : 'n/a',
          'ACC=', accumulatedFiles.length,
          'incoming=', incomingFiles.length);
      } catch(e){ /* no-op */ }
    });

    function updatePhotosCountInfo(total, max) {
      const el = document.getElementById('photosLimitInfo');
      if (!el) return;
      el.textContent = `${total}/${max} selecionadas`;
      el.style.color = total >= max ? '#ffd166' : 'var(--text-muted)';
    }

    function updateDeleteButtonVisibility() {
      if (hasUserPhotos()) {
        $("#deletePhotoBtn").fadeIn();
      } else {
        $("#deletePhotoBtn").hide();
      }
    }

    // Inicializa dots e contador na carga da página
    $(function(){
      rebuildCarouselDots();
      const hasDTCount = (typeof imagesDT !== 'undefined') && imagesDT && imagesDT.files;
      const hasAccCount = (typeof accumulatedFiles !== 'undefined') && Array.isArray(accumulatedFiles);
      const initialCount = hasDTCount ? imagesDT.files.length : (hasAccCount ? accumulatedFiles.length : 0);
      updatePhotosCountInfo(initialCount, 3);
      updateDeleteButtonVisibility();
      updateCarouselControlsVisibility();
    });

    // Envia formulário via fetch garantindo anexos do buffer de fotos, com validação de data/modo
    $("#createForm").on("submit", async function (e) {
      e.preventDefault();
      const formEl = this;

      // Validação cliente: evita enviar se data/hora não combina com modo
      const mode = $("input[name='counter_mode']:checked").val();
      const d = $("#event_date").val();
      const t = $("#event_time").val();
      if (d && t) {
        const eventDt = new Date(`${d}T${t}:00`);
        const now = new Date();
        const isFuture = eventDt.getTime() > now.getTime();
        const isPastOrNow = eventDt.getTime() <= now.getTime();
        if ((mode === "since" && !isPastOrNow) || (mode === "until" && !isFuture)) {
          if (window.Swal) {
            Swal.fire({
              icon: 'warning',
              title: 'Verifique a data e o modo',
              text: mode === 'since'
                ? "Para 'Tempo desde...', escolha uma data que já passou."
                : "Para 'Contagem para...', escolha uma data futura.",
              confirmButtonText: 'Ok'
            });
          } else {
            alert(mode === 'since'
              ? "Para 'Tempo desde...', escolha uma data que já passou."
              : "Para 'Contagem para...', escolha uma data futura.");
          }
          return; // mantém estado do formulário sem enviar
        }
      }

      const formData = new FormData(formEl);
      // Atualiza campos que podem estar somente na UI
      formData.set("image_adjustments", JSON.stringify(currentAdjustments));
      const msgVal = $("#message").val();
      if (typeof msgVal !== "undefined") {
        formData.set("optional_message", msgVal);
      }

      // Substitui os arquivos do input pelos acumulados no buffer
      formData.delete("images");
      const filesForSubmit = imagesDT && imagesDT.files && imagesDT.files.length > 0
        ? Array.from(imagesDT.files)
        : accumulatedFiles;
      try {
        console.log('[createForm] submit: filesForSubmit=', filesForSubmit.map(f => ({name: f.name, size: f.size, type: f.type})));
      } catch(e) { /* no-op */ }
      filesForSubmit.slice(0, 3).forEach((file) => formData.append("images", file));

      // Feedback de carregamento
      const $btn = $("#submitBtn");
      if ($btn.length) {
        $btn.prop("disabled", true).html('<span class="spinner-border spinner-border-sm"></span> Criando...');
      }

      try {
        const resp = await fetch(formEl.action || "/create", {
          method: "POST",
          body: formData,
          redirect: "follow",
        });
        if (resp.ok) {
          window.location.href = resp.url || (formEl.action || "/");
        } else {
          if (window.Swal) {
            Swal.fire({ icon: 'error', title: 'Erro ao criar a página', text: 'Tente novamente.' });
          } else {
            alert("Erro ao criar a página. Tente novamente.");
          }
          if ($btn.length) $btn.prop("disabled", false).text('Criar Página');
        }
      } catch (err) {
        if (window.Swal) {
          Swal.fire({ icon: 'error', title: 'Falha de rede', text: 'Verifique sua conexão.' });
        } else {
          alert("Falha de rede ao criar a página. Verifique sua conexão.");
        }
        if ($btn.length) $btn.prop("disabled", false).text('Criar Página');
      }
    });

    $("#editPhotoBtn").on("click", function () {
      if (carouselInterval) clearInterval(carouselInterval);

      const $activeImg = $(".carousel-image.active");
      if ($activeImg.length === 0) return;

      // Define a imagem e estado inicial de transformação
      activeImageIndex = $activeImg.data("index");
      if (activeImageIndex === undefined) activeImageIndex = 0;

      const src = $activeImg.attr("src");
      $("#adjustmentImage").attr("src", src);

      const adj = currentAdjustments[activeImageIndex] || { x: 0, y: 0, scale: 1, rotate: 0 };
      currentX = adj.x;
      currentY = adj.y;
      currentScale = adj.scale;
      currentRotation = adj.rotate || 0;

      $("#zoomSlider").val(currentScale);
      $("#rotateSlider").val(currentRotation);
      updateModalImageTransform();

      // Abre o modal primeiro para medir dimensões reais
      $("#photoAdjustmentModal").fadeIn(0, function () {
        try {
          // Mantém o canvas limitado ao conteúdo do modal
          $("#adjustmentContainer").css({ width: "100%", height: "" });
          // Garante visibilidade e mostra toda a imagem (contain) dentro do canvas
          $("#adjustmentImage").css({ width: "100%", height: "100%", objectFit: "contain", transformOrigin: "center", opacity: 1 });
        } catch (e) {
          // falha silenciosa caso algo mude na estrutura
        }
      });

      // Garante que não há estado de arrasto ativo ao abrir
      isDragging = false;
    });

    function updateModalImageTransform() {
      $("#adjustmentImage").css({
        "transform": `translate(${currentX}px, ${currentY}px) scale(${currentScale}) rotate(${currentRotation}deg)`,
        "transform-origin": "center"
      });
    }

    $("#zoomSlider").on("input", function () {
      currentScale = parseFloat($(this).val());
      updateModalImageTransform();
    });

    // Fallback: aplica também em 'change' para cenários onde 'input' não dispara corretamente
    $("#zoomSlider").on("change", function () {
      currentScale = parseFloat($(this).val());
      updateModalImageTransform();
    });

    // Evita que eventos do slider sejam capturados pelo container de arrasto
    $("#zoomSlider, #rotateSlider").on("mousedown touchstart", function (e) {
      e.stopPropagation();
    });

    $("#rotateSlider").on("input", function () {
      const val = parseInt($(this).val(), 10);
      currentRotation = isNaN(val) ? 0 : val;
      updateModalImageTransform();
    });

    $("#rotateSlider").on("change", function () {
      const val = parseInt($(this).val(), 10);
      currentRotation = isNaN(val) ? 0 : val;
      updateModalImageTransform();
    });

    function normalizeRotation(deg) {
      // Normaliza para o intervalo [-180, 180]
      deg = ((deg % 360) + 360) % 360; // [0, 360)
      if (deg > 180) deg -= 360; // [-180, 180]
      return deg;
    }

    $("#rotateLeft90").on("click", function () {
      currentRotation = normalizeRotation(currentRotation - 90);
      $("#rotateSlider").val(currentRotation);
      updateModalImageTransform();
    });

    $("#rotateRight90").on("click", function () {
      currentRotation = normalizeRotation(currentRotation + 90);
      $("#rotateSlider").val(currentRotation);
      updateModalImageTransform();
    });

    const $container = $("#adjustmentContainer");

    $container.on("mousedown", function (e) {
      isDragging = true;
      startX = e.clientX - currentX;
      startY = e.clientY - currentY;
      $(this).css("cursor", "grabbing");
    });

    $(document).on("mousemove", function (e) {
      if (!isDragging) return;
      e.preventDefault();
      currentX = e.clientX - startX;
      currentY = e.clientY - startY;
      updateModalImageTransform();
    });

    $(document).on("mouseup", function () {
      if (isDragging) {
        isDragging = false;
        $container.css("cursor", "grab");
      }
    });

    // Suporte a toque no mobile para arrastar a imagem dentro do container
    $container.on("touchstart", function (e) {
      if (!e.originalEvent || !e.originalEvent.touches || e.originalEvent.touches.length === 0) return;
      const t = e.originalEvent.touches[0];
      isDragging = true;
      startX = t.clientX - currentX;
      startY = t.clientY - currentY;
      $(this).css("cursor", "grabbing");
    });

    $(document).on("touchmove", function (e) {
      if (!isDragging) return;
      if (!e.originalEvent || !e.originalEvent.touches || e.originalEvent.touches.length === 0) return;
      const t = e.originalEvent.touches[0];
      // Evita que a página role enquanto ajusta a imagem
      e.preventDefault();
      currentX = t.clientX - startX;
      currentY = t.clientY - startY;
      updateModalImageTransform();
    });

    $(document).on("touchend touchcancel", function () {
      if (isDragging) {
        isDragging = false;
        $container.css("cursor", "grab");
      }
    });

    $("#saveAdjustmentBtn").on("click", function () {
      currentAdjustments[activeImageIndex] = {
        x: currentX,
        y: currentY,
        scale: currentScale,
        rotate: currentRotation
      };

      const $img = $(`.carousel-image[data-index='${activeImageIndex}']`);
      applyAdjustmentVars(activeImageIndex, $img);
    $img.css({ "transform-origin": "center" });

      $("#imageAdjustments").val(JSON.stringify(currentAdjustments));

      $("#photoAdjustmentModal").fadeOut();
      startCarousel();
    });

    $("#cancelAdjustmentBtn").on("click", function () {
      $("#photoAdjustmentModal").fadeOut();
      startCarousel();
    });

    // Background Preview
    $("#backgroundSelector").on("change", function () {
      const bg = $(this).val();
      // Remove qualquer classe de tema anterior (gradiente_*, texture_*) para evitar conflito
      $("body").removeClass((i, c) => (c.match(/(^|\s)(gradient_|texture_)\S+/g) || []).join(' '));
      if (bg) $("body").addClass(bg);
    });

    // Text Theme Preview (aplica classe nos elementos especiais)
    $("#textThemeSelector").on("change", function () {
      const theme = $(this).val();
      const $targets = $("#e_comercial, #event_description_text, #carouselDots");
      const $msgTargets = $("#optional_message_text .themed-text");
      // Remove classes anteriores de tema
      $targets.add($msgTargets).removeClass(function (i, c) {
        return (c.match(/(^|\s)text_theme_\S+/g) || []).join(' ');
      });
      if (theme) {
        $targets.addClass(theme);
        $msgTargets.addClass(theme);
      }
    });
    // Inicializa tema de texto na prévia
    (function initTextTheme() {
      const theme = $("#textThemeSelector").val() || $("#textThemeSelector").attr("value");
      const $targets = $("#e_comercial, #event_description_text, #carouselDots");
      const $msgTargets = $("#optional_message_text .themed-text");
      $targets.add($msgTargets).removeClass(function (i, c) {
        return (c.match(/(^|\s)text_theme_\S+/g) || []).join(' ');
      });
      if (theme) {
        $targets.addClass(theme);
        $msgTargets.addClass(theme);
      }
    })();

    // Mensagem opcional padrão na prévia
    (function initDefaultMessage(){
      const defaultMsgRaw = "💖 Cada dia ao seu lado torna nossa história mais linda ✨\nObrigado por caminhar comigo, por cada sorriso 😊 e por todo o carinho 💞📸\nQue nosso amor siga crescendo — hoje, amanhã e sempre ♾️💫";
      const $msg = $("#message");
      const $preview = $("#optional_message_text");
      if (!$msg.val()) {
        $msg.val(defaultMsgRaw);
      }
      const html = renderMessageWithEmojiIsolation($msg.val());
      $preview.html(html);
    })();

    // YouTube Preview
    function extractYouTubeId(url) {
      const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
      const match = url.match(regExp);
      return (match && match[2].length === 11) ? match[2] : null;
    }

    function renderVideoPreviewById(videoId) {
      const $videoContainer = $("#videoPreviewContainer");
      $videoContainer.empty();
      if (!videoId) { $videoContainer.hide(); return; }
      const $cover = $(
        `<div class="video-cover" style="
            width: 100%; height: 300px; background: linear-gradient(135deg, #1a1a1a, #2c2c2c);
            display:flex; flex-direction:column; align-items:center; justify-content:center; cursor:pointer; position:relative; border-radius:16px;">
           <div style="font-size: 3rem; margin-bottom: 1rem;">🎁</div>
           <h4 style="color: white; margin-bottom: 0.5rem;">Vídeo Surpresa</h4>
           <p style="color: #aaa; font-size: 0.9rem;">Clique para assistir (com som) 🔊</p>
           <div style="position:absolute; inset:0; background: rgba(255,255,255,0.05); opacity:0; transition:opacity .3s; border-radius:16px;"></div>
         </div>`
      );
      $cover.hover(
        function(){ $(this).find('div:last-child').css('opacity',1); },
        function(){ $(this).find('div:last-child').css('opacity',0); }
      );
      $cover.on('click', function(){
        const embedUrl = `https://www.youtube-nocookie.com/embed/${videoId}?rel=0&modestbranding=1&autoplay=1&playsinline=1`;
        const iframe = $(`<iframe src="${embedUrl}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen style="width: 100%; height: 300px; border: none;"></iframe>`);
        $videoContainer.empty().append(iframe);
        const $fallback = $(`<div style="margin-top: 8px; text-align: center;"><a href="https://www.youtube.com/watch?v=${videoId}" target="_blank" rel="noopener" style="color:#0077ff;">Abrir no YouTube</a></div>`);
        $videoContainer.append($fallback);
      });
      $videoContainer.append($cover).show();
    }

    $("#youtubeLink").on("input", function () {
      const url = $(this).val();
      const videoId = extractYouTubeId(url);
      if (videoId) {
        renderVideoPreviewById(videoId);
      } else {
        // Se o campo ficar em branco, mostrar apenas o demo padrão na prévia
        const defaultDemoId = "OgSzWo1uUH4";
        renderVideoPreviewById(defaultDemoId);
      }
    });
    // Inicializa a prévia com vídeo padrão, sem preencher o campo
    (function initYouTubeDefault(){
      renderVideoPreviewById("OgSzWo1uUH4");
    })();

    // Inicializa prévia da data selecionada
    updateSelectedDateHint();
  }

  // (handler removido — validação e submit agora estão integrados ao handler de fetch)
});

// Detecta suporte a background-clip: text para habilitar gradiente no texto sem fundo retangular
(function() {
  try {
    var supportsClip = false;
    if (window.CSS && CSS.supports) {
      supportsClip = CSS.supports('background-clip', 'text') || CSS.supports('-webkit-background-clip', 'text');
    }
    if (supportsClip) {
      document.body.classList.add('supports-text-clip');
    } else {
      document.body.classList.remove('supports-text-clip');
    }
  } catch (e) {
    document.body.classList.remove('supports-text-clip');
  }
})();
