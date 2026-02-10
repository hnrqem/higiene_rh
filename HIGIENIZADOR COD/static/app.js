document.addEventListener("DOMContentLoaded", () => {
    // Feedback ao selecionar arquivos
    const inputs = document.querySelectorAll('input[type="file"]');
    inputs.forEach(input => {
        input.addEventListener("change", (e) => {
            const fileName = e.target.files[0]?.name;
            const label = input.closest('label');
            if (fileName && label) {
                label.querySelector('span').innerText = fileName;
                label.querySelector('i').style.color = "#4ade80";
                label.style.borderColor = "#4ade80";
            }
        });
    });

    // Animação de Loading no botão
    const forms = document.querySelectorAll("form");
    forms.forEach(form => {
        form.addEventListener("submit", () => {
            const btn = form.querySelector('button');
            if (btn) {
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processando...';
                btn.classList.add('loading');
                btn.style.pointerEvents = 'none';
                btn.style.opacity = '0.8';
            }
        });
    });
});