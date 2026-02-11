document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form");
    const alertBox = document.getElementById("js-alert");

    console.log("🚀 Sistema de validação carregado!");

    // 1. Lógica de Feedback Visual (Quando seleciona o arquivo)
    document.addEventListener("change", (e) => {
        if (e.target.type === "file") {
            const input = e.target;
            const label = input.closest('label');
            
            if (label && input.files[0]) {
                const span = label.querySelector('span');
                const icon = label.querySelector('i');

                if (span) span.innerText = input.files[0].name;
                if (icon) {
                    icon.className = "fa-solid fa-file-circle-check";
                    icon.style.color = "#4ade80";
                }
                label.style.borderColor = "#4ade80";
                label.style.background = "rgba(74, 222, 128, 0.05)";

                // Esconde o alerta de erro se o usuário corrigiu o problema
                if (alertBox) alertBox.style.display = "none";
            }
        }
    });

    // 2. Validação Customizada (Ao enviar)
    if (form) {
        form.addEventListener("submit", function(e) {
            const fileInputs = form.querySelectorAll('input[type="file"]');
            let faltamArquivos = false;

            fileInputs.forEach(input => {
                if (input.files.length === 0) {
                    faltamArquivos = true;
                }
            });

            if (faltamArquivos) {
                // Bloqueia o envio nativo
                e.preventDefault();
                
                // Exibe o alerta elegante na página
                if (alertBox) {
                    alertBox.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Por favor, selecione os arquivos obrigatórios.';
                    alertBox.style.display = "flex";
                }
            } else {
                // Se estiver tudo OK, inicia o Loading
                const btn = form.querySelector('button[type="submit"]');
                if (btn) {
                    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processando...';
                    btn.style.opacity = "0.7";
                    btn.style.pointerEvents = "none";
                }
                if (alertBox) alertBox.style.display = "none";
            }
        });
    }
});
