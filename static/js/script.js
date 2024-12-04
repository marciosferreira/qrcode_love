document.addEventListener('DOMContentLoaded', function() {
    var dateInput = document.getElementById('event_date');
    var today = new Date().toISOString().split('T')[0];
    dateInput.setAttribute('max', today);
});
