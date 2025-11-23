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

  // Default to current date if not provided (for preview)
  if (!eventDateStr) {
    const now = new Date();
    eventDateStr = now.toISOString().split('T')[0];
    eventTimeStr = "00:00";
  }

  let eventDate = new Date(`${eventDateStr}T${eventTimeStr}:00`);

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
    const currentDate = getManausTime();
    let timeDiff;

    // Re-read mode from DOM in case it changed (preview)
    counterMode = $eventData.data("counter-mode") || "since";

    // Caso incoerente: modo "Desde" com data futura → mostrar mensagem e não contar
    if (counterMode === "since" && currentDate.getTime() < eventDate.getTime()) {
      const $prefix = $("#counter_prefix_text");
      if ($prefix.length) $prefix.text("Ainda não começou:");
      $counterContainer.html('<div class="glass-card" style="padding: 1rem;"><h3 style="margin:0;">Evento ainda não chegou</h3></div>');
      return;
    }

    if (counterMode === "until") {
      timeDiff = eventDate.getTime() - currentDate.getTime();
    } else {
      timeDiff = currentDate.getTime() - eventDate.getTime();
    }

    // Countdown finished
    if (counterMode === "until" && timeDiff <= 0) {
      $counterContainer.html('<div class="glass-card" style="padding: 1rem;"><h3 style="margin:0;">❤️ O evento chegou! ❤️</h3></div>');
      return;
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

    $counterContainer.html(html);
  }

  // Start Timer
  setInterval(updateCounter, 1000);
  updateCounter();

  /* =========================================
     CAROUSEL LOGIC
     ========================================= */
  let carouselInterval;
  function startCarousel() {
    if (carouselInterval) clearInterval(carouselInterval);

    carouselInterval = setInterval(() => {
      const $images = $(".carousel-image");
      if ($images.length <= 1) return;

      const $active = $images.filter(".active");
      let $next = $active.next("img");
      if ($next.length === 0) $next = $images.first();

      $active.removeClass("active").css("opacity", 0);
      $next.addClass("active").css("opacity", 1);
    }, 3000);
  }

  startCarousel();

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
    if (!type || type === "none") return;

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
    // Update Date/Time
    $("#event_date, #event_time").on("change", function () {
      const d = $("#event_date").val();
      const t = $("#event_time").val();
      if (d && t) {
        eventDate = new Date(`${d}T${t}:00`);
        updateCounter();
      }
    });

    // Update Names
    $("#name1, #name2").on("input", function () {
      const n1 = $("#name1").val() || "Nome 1";
      const n2 = $("#name2").val();

      $("#couple_name1").text(n1);
      if (n2) {
        $("#couple_name2").text(n2).show();
        $("#e_comercial").show();
      } else {
        $("#couple_name2").hide();
        $("#e_comercial").hide();
      }
    });

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
        "Relacionamentos amorosos 💑": [
          { value: "se casarem", singular: "se casar", plural: "se casarem" },
          { value: "noivarem", singular: "noivar", plural: "noivarem" },
          { value: "morarem juntos", singular: "morar junto", plural: "morarem juntos" },
          { value: "a lua de mel", singular: "a lua de mel", plural: "a lua de mel" },
          { value: "renovarem os votos", singular: "renovar os votos", plural: "renovarem os votos" }
        ],
        "Família e Amigos 👨‍👩‍👧‍👦": [
          { value: "se reencontrarem", singular: "se reencontrar", plural: "se reencontrarem" },
          { value: "o nascimento do bebê", singular: "o nascimento do bebê", plural: "o nascimento do bebê" },
          { value: "a festa de 15 anos", singular: "a festa de 15 anos", plural: "a festa de 15 anos" }
        ],
        "Conquistas e Planos 🚀": [
          { value: "a formatura", singular: "a formatura", plural: "a formatura" },
          { value: "a viagem dos sonhos", singular: "a viagem dos sonhos", plural: "a viagem dos sonhos" },
          { value: "a aposentadoria", singular: "a aposentadoria", plural: "a aposentadoria" },
          { value: "a mudança de casa", singular: "a mudança de casa", plural: "a mudança de casa" },
          { value: "realizar um sonho", singular: "realizar um sonho", plural: "realizarem um sonho" }
        ]
      }
    };

    function updateEventSelectOptions(mode) {
      const $select = $("#eventSelect");
      const currentVal = $select.val();
      const hasSecondName = $("#name2").val().trim().length > 0;
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
    }

    function updateDescriptionAndMode() {
      const mode = $("input[name='counter_mode']:checked").val();
      const useCustom = $("#customPhraseToggle").is(":checked");
      const customText = $("#customPhraseInput").val();
      // Use o texto exibido da opção, que já respeita singular/plural
      const selectText = $("#eventSelect option:selected").text();
      const hasSecondName = $("#name2").val().trim().length > 0;

      $eventData.data("counter-mode", mode);
      $("#counter_prefix_text").text(mode === "until" ? "Faltam:" : "Já se passaram:");

      const prefix = mode === "until" ? "para " : "desde que ";
      let mainText = useCustom && customText ? customText : selectText;

      // Texto padrão quando nada foi selecionado/digitado
      if (!mainText) {
        if (mode === "until") {
          mainText = hasSecondName ? "se casarem" : "se casar";
        } else {
          mainText = hasSecondName ? "se casaram" : "se casou";
        }
      }

      $("#event_description_text").text(prefix + mainText);

      if (useCustom) {
        $("#customPhraseInput").removeClass("d-none");
        $("#eventSelect").addClass("d-none");
        $("#descriptionMode").val("custom");
      } else {
        $("#customPhraseInput").addClass("d-none");
        $("#eventSelect").removeClass("d-none");
        $("#descriptionMode").val("select");
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

    // Atualiza opções e descrição ao digitar o primeiro nome (garante singular)
    $("#name1").on("input", function () {
      const mode = $("input[name='counter_mode']:checked").val();
      updateEventSelectOptions(mode);
      updateDescriptionAndMode();
    });

    // Inicializa opções e descrição na carga da página
    (function initPreview() {
      const mode = $("input[name='counter_mode']:checked").val();
      updateEventSelectOptions(mode);
      updateDescriptionAndMode();
    })();

    $("#message").on("input", function () {
      const msg = $(this).val();
      $("#optional_message_text").text(msg || "Sua mensagem aparecerá aqui...");
    });

    // Validação de modo/data na submissão
    $("#createForm").on("submit", function (e) {
      const d = $("#event_date").val();
      const t = $("#event_time").val();
      const mode = $("input[name='counter_mode']:checked").val();

      if (!d || !t || !mode) return; // Campos obrigatórios já cobrem ausência

      // Validação simples usando o horário local do navegador
      const eventMs = new Date(`${d}T${t}:00`).getTime();
      const nowMs = Date.now();

      if (mode === "since" && eventMs > nowMs) {
        e.preventDefault();
        if (window.Swal) {
          Swal.fire({
            icon: 'warning',
            title: 'Evento ainda não chegou',
            text: "Para 'Tempo desde...', escolha uma data que já passou ou mude para 'Contagem para...'.",
            confirmButtonText: 'Entendi'
          });
        } else {
          alert("Para 'Tempo desde...', escolha uma data que já passou ou mude para 'Contagem para...'.");
        }
      }

      if (mode === "until" && eventMs <= nowMs) {
        e.preventDefault();
        if (window.Swal) {
          Swal.fire({
            icon: 'error',
            title: 'O evento já chegou',
            text: "Para 'Contagem para...', escolha uma data futura ou mude para 'Tempo desde...'.",
            confirmButtonText: 'Entendi'
          });
        } else {
          alert("Para 'Contagem para...', escolha uma data futura ou mude para 'Tempo desde...'.");
        }
      }
    });

    // Photo Adjustment
    let currentAdjustments = {};
    let isDragging = false;
    let startX, startY, currentX = 0, currentY = 0, currentScale = 1, currentRotate = 0;
    let activeImageIndex = 0;

    function updateEditButtonVisibility() {
      if ($(".carousel-image").length > 0) {
        $("#editPhotoBtn").fadeIn();
      } else {
        $("#editPhotoBtn").hide();
      }
    }

    $("#images").on("change", function () {
      const files = this.files;
      const $carousel = $("#carousel");
      $carousel.find("img").remove();
      currentAdjustments = {};
      $("#imageAdjustments").val("");

      if (files.length === 0) {
        $carousel.prepend('<img src="https://meueventoespecial.com.br/static/images/placeholder.png" class="carousel-image active" style="width: 100%; height: 100%; object-fit: contain; position: absolute; top: 0; left: 0;">');
        updateEditButtonVisibility();
        return;
      }

      let loadedCount = 0;
      const totalFiles = files.length;

      Array.from(files).forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = function (e) {
          const activeClass = index === 0 ? "active" : "";
          const img = $(`<img src="${e.target.result}" class="carousel-image ${activeClass}" data-index="${index}" style="width: 100%; height: 100%; object-fit: contain; position: absolute; top: 0; left: 0; opacity: ${index === 0 ? 1 : 0}; transition: opacity 1s;">`);
          $carousel.prepend(img);

          loadedCount++;
          if (loadedCount === totalFiles) {
            startCarousel();
            updateEditButtonVisibility();
          }
        }
        reader.readAsDataURL(file);
      });
    });

    $("#editPhotoBtn").on("click", function () {
      if (carouselInterval) clearInterval(carouselInterval);

      const $activeImg = $(".carousel-image.active");
      if ($activeImg.length === 0) return;

      activeImageIndex = $activeImg.data("index");
      if (activeImageIndex === undefined) activeImageIndex = 0;

      const src = $activeImg.attr("src");
      $("#adjustmentImage").attr("src", src);

      const adj = currentAdjustments[activeImageIndex] || { x: 0, y: 0, scale: 1, rotate: 0 };
      currentX = adj.x;
      currentY = adj.y;
      currentScale = adj.scale;
      currentRotate = adj.rotate || 0;

      $("#zoomSlider").val(currentScale);
      $("#rotateSlider").val(currentRotate);
      updateModalImageTransform();

      $("#photoAdjustmentModal").fadeIn();
    });

    function updateModalImageTransform() {
      $("#adjustmentImage").css("transform", `translate(${currentX}px, ${currentY}px) scale(${currentScale}) rotate(${currentRotate}deg)`);
    }

    $("#zoomSlider").on("input", function () {
      currentScale = parseFloat($(this).val());
      updateModalImageTransform();
    });

    $("#rotateSlider").on("input", function () {
      currentRotate = parseInt($(this).val(), 10);
      updateModalImageTransform();
    });

    function normalizeAngle(angle) {
      // Mantém ângulo entre -180 e 180
      let a = ((angle + 180) % 360 + 360) % 360 - 180;
      return a;
    }

    $("#rotateLeft90").on("click", function () {
      currentRotate = normalizeAngle(currentRotate - 90);
      $("#rotateSlider").val(currentRotate);
      updateModalImageTransform();
    });

    $("#rotateRight90").on("click", function () {
      currentRotate = normalizeAngle(currentRotate + 90);
      $("#rotateSlider").val(currentRotate);
      updateModalImageTransform();
    });

    const $container = $("#adjustmentContainer");

    function beginDrag(clientX, clientY) {
      isDragging = true;
      startX = clientX - currentX;
      startY = clientY - currentY;
    }

    function moveDrag(clientX, clientY) {
      currentX = clientX - startX;
      currentY = clientY - startY;
      updateModalImageTransform();
    }

    function endDrag() {
      isDragging = false;
    }

    // Mouse events (desktop)
    $container.on("mousedown", function (e) {
      beginDrag(e.clientX, e.clientY);
      $(this).css("cursor", "grabbing");
    });

    $(document).on("mousemove", function (e) {
      if (!isDragging) return;
      e.preventDefault();
      moveDrag(e.clientX, e.clientY);
    });

    $(document).on("mouseup", function () {
      if (!isDragging) return;
      endDrag();
      $container.css("cursor", "grab");
    });

    // Touch events (mobile)
    $container.on("touchstart", function (e) {
      const t = e.originalEvent.touches && e.originalEvent.touches[0];
      if (!t) return;
      beginDrag(t.clientX, t.clientY);
    });

    $(document).on("touchmove", function (e) {
      if (!isDragging) return;
      const t = e.originalEvent.touches && e.originalEvent.touches[0];
      if (!t) return;
      e.preventDefault();
      moveDrag(t.clientX, t.clientY);
    });

    $(document).on("touchend touchcancel", function () {
      if (!isDragging) return;
      endDrag();
    });

    $("#saveAdjustmentBtn").on("click", function () {
      currentAdjustments[activeImageIndex] = {
        x: currentX,
        y: currentY,
        scale: currentScale,
        rotate: currentRotate
      };

      const $img = $(`.carousel-image[data-index='${activeImageIndex}']`);
      $img.css("transform", `translate(${currentX}px, ${currentY}px) scale(${currentScale}) rotate(${currentRotate}deg)`);

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
      // Remove qualquer classe de tema previamente aplicada (gradientes e texturas)
      $("body").removeClass((i, c) => (c.match(/(^|\s)(gradient|texture)_\S+/g) || []).join(' '));
      if (bg) $("body").addClass(bg);
    });

    // YouTube Preview
    function extractYouTubeId(url) {
      const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
      const match = url.match(regExp);
      return (match && match[2].length === 11) ? match[2] : null;
    }

    $("#youtubeLink").on("input", function () {
      const url = $(this).val();
      const videoId = extractYouTubeId(url);
      const $videoContainer = $("#videoPreviewContainer");

      $videoContainer.empty();

      if (videoId) {
        const $cover = $(`
          <div class="video-cover" style="
              width: 100%; 
              height: 300px; 
              background: linear-gradient(135deg, #1a1a1a, #2c2c2c); 
              display: flex; 
              flex-direction: column; 
              align-items: center; 
              justify-content: center; 
              cursor: pointer; 
              position: relative;
          ">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🎁</div>
            <h4 style="color: white; margin-bottom: 0.5rem;">Vídeo Surpresa</h4>
            <p style="color: #aaa; font-size: 0.9rem;">Clique para assistir (com som) 🔊</p>
            <div style="
                position: absolute; 
                top: 0; left: 0; width: 100%; height: 100%; 
                background: rgba(255,255,255,0.05); 
                opacity: 0; 
                transition: opacity 0.3s;
            "></div>
          </div>
        `);

        $cover.hover(
          function () { $(this).find("div:last-child").css("opacity", 1); },
          function () { $(this).find("div:last-child").css("opacity", 0); }
        );

        $cover.on("click", function () {
          const iframe = $(`<iframe src="https://www.youtube.com/embed/${videoId}?autoplay=1&mute=0&controls=1&loop=0" 
                                  frameborder="0" 
                                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                                  allowfullscreen
                                  style="width: 100%; height: 300px; border: none;"></iframe>`);
          $videoContainer.empty().append(iframe);
        });

        $videoContainer.append($cover).show();
      } else {
        $videoContainer.hide();
      }
    });
  }

  $("#createForm").on("submit", function () {
    const $btn = $("#submitBtn");
    $btn.prop("disabled", true).html('<span class="spinner-border spinner-border-sm"></span> Criando...');
  });
});
