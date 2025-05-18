document.addEventListener("DOMContentLoaded", function () {
  var dateInput = document.getElementById("event_date");
  var today = new Date().toISOString().split("T")[0];
  dateInput.setAttribute("max", today);
});

function adjustCarouselHeight() {
  const activeImage = document.querySelector(".carousel-image.active");
  const container = document.getElementById("carousel");
  if (activeImage) {
    setTimeout(() => {
      container.style.height = activeImage.offsetHeight + "px";
    }, 100); // espera a imagem renderizar
  }
}

// Chame sempre que a imagem mudar
setInterval(() => {
  adjustCarouselHeight();
}, 3100); // um pouco mais que o intervalo do carrossel
