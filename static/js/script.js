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

    if (counterMode === "until") {
      timeDiff = eventDate.getTime() - currentDate.getTime();
    } else {
      timeDiff = currentDate.getTime() - eventDate.getTime();
    }

    // Countdown finished: show message with exact date/time and keep counter zeroed
    let finishedMsg = "";
    if (counterMode === "until" && timeDiff <= 0) {
      // Force zero values in the boxes
      timeDiff = 0;

      // Format event date/time in Manaus timezone as dd/mm/yy às hh:mm
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
      const selectText = $("#eventSelect").val();

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

    $("#message").on("input", function () {
      const msg = $(this).val();
      $("#optional_message_text").text(msg || "Sua mensagem aparecerá aqui...");
    });

    // Inicializa descrição com base no modo atual e primeira opção
    (function initDescription() {
      const initMode = $("input[name='counter_mode']:checked").val();
      updateEventSelectOptions(initMode);
      updateDescriptionAndMode();
    })();

    // Photo Adjustment
    // Buffer de arquivos para acumular seleções múltiplas do input
    let imagesDT;
    try {
      imagesDT = new DataTransfer();
    } catch (e) {
      imagesDT = null; // fallback para navegadores sem DataTransfer
    }
    const accumulatedFiles = [];
    let currentAdjustments = {};
    let isDragging = false;
    let startX, startY, currentX = 0, currentY = 0, currentScale = 1, currentRotation = 0;
    let activeImageIndex = 0;

    function updateEditButtonVisibility() {
      if ($(".carousel-image").length > 0) {
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
          return src.includes("placeholder.png");
        })
        .remove();

      const existingCount = $carousel.find(".carousel-image").length;

      // Adiciona os novos arquivos ao buffer (máximo 3), evitando duplicados
      const maxPhotos = 3;
      const filesToAppend = [];
      const currentCountDT = imagesDT ? imagesDT.files.length : 0;
      const currentCountAcc = accumulatedFiles.length;

      incomingFiles.forEach((file) => {
        // Respeita limite somando buffer atual
        const totalCount = (imagesDT ? imagesDT.files.length : 0) + accumulatedFiles.length;
        if (totalCount >= maxPhotos) return;
        // Evita duplicados
        const isDupDT = imagesDT ? Array.from(imagesDT.files).some(
          (f) => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified
        ) : false;
        const isDupAcc = accumulatedFiles.some(
          (f) => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified
        );
        if (isDupDT || isDupAcc) return;

        // Adiciona ao buffer disponível
        if (imagesDT && imagesDT.items) imagesDT.items.add(file);
        accumulatedFiles.push(file);
        filesToAppend.push(file);
      });
      // Garante que o formulário enviará todas as fotos acumuladas
      const imagesInput = document.getElementById("images");
      if (imagesInput && imagesDT) imagesInput.files = imagesDT.files;

      const totalBuffered = (imagesDT ? imagesDT.files.length : 0) + accumulatedFiles.length;
      if (totalBuffered === 0 && existingCount === 0) {
        $carousel.prepend('<img src="https://meueventoespecial.com.br/static/images/placeholder.png" class="carousel-image active" style="width: 100%; height: 100%; object-fit: cover; position: absolute; top: 0; left: 0;">');
        updateEditButtonVisibility();
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
          const img = $(`<img src="${e.target.result}" class="carousel-image ${activeClass}" data-index="${dataIndex}" style="width: 100%; height: 100%; object-fit: cover; position: absolute; top: 0; left: 0; opacity: ${initialOpacity}; transition: opacity 1s;">`);
          $carousel.append(img);

          loadedCount++;
          if (loadedCount === totalFiles) {
            // Atualiza campo oculto com ajustes atuais (preservados)
            $("#imageAdjustments").val(JSON.stringify(currentAdjustments));
            startCarousel();
            updateEditButtonVisibility();
          }
        };
        reader.readAsDataURL(file);
      });

      // Limpa valor do input para permitir adicionar novamente o mesmo arquivo se desejado
      inputEl.value = "";
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

      $("#photoAdjustmentModal").fadeIn();
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
      $img.css({
        "transform": `translate(${currentX}px, ${currentY}px) scale(${currentScale}) rotate(${currentRotation}deg)`,
        "transform-origin": "center"
      });

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
      const $targets = $("#e_comercial, #event_description_text, #optional_message_text");
      // Remove classes anteriores de tema
      $targets.removeClass(function (i, c) {
        return (c.match(/(^|\s)text_theme_\S+/g) || []).join(' ');
      });
      if (theme) $targets.addClass(theme);
    });
    // Inicializa tema de texto na prévia
    (function initTextTheme() {
      const theme = $("#textThemeSelector").val() || $("#textThemeSelector").attr("value");
      const $targets = $("#e_comercial, #event_description_text, #optional_message_text");
      $targets.removeClass(function (i, c) {
        return (c.match(/(^|\s)text_theme_\S+/g) || []).join(' ');
      });
      if (theme) $targets.addClass(theme);
    })();

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
