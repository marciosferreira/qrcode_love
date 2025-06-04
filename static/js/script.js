$(document).ready(function () {
  $("#name1").on("input", function () {
    $("#couple_name1").text($(this).val() || "Nome 1");
  });

  $("#name2").on("input", function () {
    $("#couple_name2").text($(this).val() || "Nome 2");
  });

  $("#event_description").on("change", function () {
    const selectedValue = $(this).val();
    $("#event_description_text").text("desde que " + selectedValue);
  });

  $("#message").on("input", function () {
    $("#optional_message_text").text(
      $(this).val() || "Mensagem opcional será exibida aqui"
    );
  });

  let eventDate = new Date("2023-01-01T00:00:00");

  function getManausTime() {
    let now = new Date();
    let options = {
      timeZone: "America/Manaus",
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "numeric",
      second: "numeric",
      hour12: false,
    };
    let formatter = new Intl.DateTimeFormat("en-US", options);
    let parts = formatter.formatToParts(now);

    let year = parts.find((part) => part.type === "year").value;
    let month = parts.find((part) => part.type === "month").value - 1;
    let day = parts.find((part) => part.type === "day").value;
    let hour = parts.find((part) => part.type === "hour").value;
    let minute = parts.find((part) => part.type === "minute").value;
    let second = parts.find((part) => part.type === "second").value;

    return new Date(year, month, day, hour, minute, second);
  }

  function updateCounter() {
    var currentDate = getManausTime();
    var timeDiff = currentDate.getTime() - eventDate.getTime();

    if (timeDiff < 0) {
      timeDiff = Math.abs(timeDiff);
    }

    var seconds = Math.floor(timeDiff / 1000);
    var minutes = Math.floor(seconds / 60);
    var hours = Math.floor(minutes / 60);
    var days = Math.floor(hours / 24);
    var months = Math.floor(days / 30);
    var years = Math.floor(months / 12);

    months %= 12;
    days %= 30;
    hours %= 24;
    minutes %= 60;
    seconds %= 60;

    var result = "";

    if (years > 0) {
      result += `<div class="time-unit-container"><div class="time-unit">${years}</div><div class="label">${
        years == 1 ? "ano" : "anos"
      }</div></div>`;
    }
    if (months > 0) {
      result += `<div class="time-unit-container"><div class="time-unit">${months}</div><div class="label">${
        months == 1 ? "mês" : "meses"
      }</div></div>`;
    }
    if (days > 0) {
      result += `<div class="time-unit-container"><div class="time-unit">${days}</div><div class="label">${
        days == 1 ? "dia" : "dias"
      }</div></div>`;
    }
    if (hours > 0) {
      result += `<div class="time-unit-container"><div class="time-unit">${hours}</div><div class="label">${
        hours == 1 ? "hora" : "horas"
      }</div></div>`;
    }
    if (minutes > 0) {
      result += `<div class="time-unit-container"><div class="time-unit">${minutes}</div><div class="label">${
        minutes == 1 ? "minuto" : "minutos"
      }</div></div>`;
    }
    result += `<div class="time-unit-container"><div class="time-unit">${seconds}</div><div class="label">${
      seconds == 1 ? "segundo" : "segundos"
    }</div></div>`;

    const counterElement = document.getElementById("meu-contador");
    if (counterElement) {
      counterElement.innerHTML = result;
    }
  }

  // Initialize counter immediately
  updateCounter();
  setInterval(updateCounter, 1000);

  $("#event_date").on("change", function () {
    let selectedDate = $(this).val();
    let selectedTime = $("#event_time").val() || "00:00";
    if (selectedDate) {
      eventDate = new Date(`${selectedDate}T${selectedTime}:00`);
      updateCounter();
    }
  });

  $("#event_time").on("change", function () {
    let selectedTime = $(this).val();
    let selectedDate = $("#event_date").val() || "2023-01-01";
    if (selectedTime) {
      eventDate = new Date(`${selectedDate}T${selectedTime}:00`);
      updateCounter();
    }
  });

  // Carousel functionality
  let carouselInterval;

  function restartCarousel() {
    if (carouselInterval) clearInterval(carouselInterval);

    let currentIndex = 0;
    const carouselImages = document.querySelectorAll(
      "#carousel .carousel-image"
    );

    carouselImages.forEach((img, i) => {
      img.classList.remove("active");
      if (i === 0) img.classList.add("active");
    });

    if (carouselImages.length > 1) {
      carouselInterval = setInterval(() => {
        carouselImages[currentIndex].classList.remove("active");
        currentIndex = (currentIndex + 1) % carouselImages.length;
        carouselImages[currentIndex].classList.add("active");
      }, 3000);
    }
  }

  // Handle image upload
  const imagesInput = document.getElementById("images");
  const carousel = document.getElementById("carousel");

  imagesInput.addEventListener("change", function () {
    const files = imagesInput.files;
    const total = files.length;

    // Remove imagens antigas
    carousel.querySelectorAll(".carousel-image").forEach((img) => img.remove());

    // Se não houver imagens, volta o placeholder
    if (total === 0) {
      const placeholder = document.createElement("img");
      placeholder.src = "/static/images/placeholder.png";
      placeholder.className = "carousel-image active";
      placeholder.alt = "Imagem inicial";
      carousel.appendChild(placeholder);
      restartCarousel();
      return;
    }

    let loadedCount = 0;

    for (let i = 0; i < total; i++) {
      const file = files[i];
      const reader = new FileReader();

      reader.onload = function (e) {
        const newImage = document.createElement("img");
        newImage.src = e.target.result;
        newImage.className = "carousel-image";
        if (i === 0) newImage.classList.add("active");

        newImage.style.width = "100%";
        newImage.style.height = "100%";
        newImage.style.objectFit = "cover";

        carousel.appendChild(newImage);
        loadedCount++;

        if (loadedCount === total) {
          // Garante que o container de efeito seja o último (z-index alto)
          const effect = document.getElementById("presentationEffectContainer");
          if (effect && effect.parentNode !== carousel) {
            carousel.appendChild(effect);
          }

          restartCarousel();
        }
      };

      reader.readAsDataURL(file);
    }
  });

  // Função de rotação automática do carrossel
  function restartCarousel() {
    const images = document.querySelectorAll("#carousel .carousel-image");
    let index = 0;

    // Resetar visibilidade
    images.forEach((img, i) => {
      img.classList.remove("active");
      if (i === 0) img.classList.add("active");
    });

    if (images.length < 2) return;

    clearInterval(window._carouselInterval);

    window._carouselInterval = setInterval(() => {
      images[index].classList.remove("active");
      index = (index + 1) % images.length;
      images[index].classList.add("active");
    }, 3000);
  }

  // Inicializa carrossel no carregamento
  restartCarousel();
});
