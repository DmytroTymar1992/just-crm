document.addEventListener('DOMContentLoaded', function() {
    const copyButtons = document.querySelectorAll('.copy-link-btn');

    copyButtons.forEach(button => {
        button.addEventListener('click', async function() {
            let link = this.getAttribute('data-link');

            // Якщо рядок містить екрановані символи, декодуємо його
            try {
                // Декодування Unicode-послідовностей
                link = decodeURIComponent(link.replace(/\\u([\dA-F]{4})/gi, (match, grp) => {
                    return String.fromCharCode(parseInt(grp, 16));
                }));

                await navigator.clipboard.writeText(link);
                this.innerHTML = '<i class="bi bi-check2"></i>';
                this.classList.remove('btn-outline-info');
                this.classList.add('btn-success');

                setTimeout(() => {
                    this.innerHTML = '<i class="bi bi-link-45deg"></i>';
                    this.classList.remove('btn-success');
                    this.classList.add('btn-outline-info');
                }, 2000);
            } catch (error) {
                console.error('Помилка при копіюванні:', error);
                alert('Не вдалося скопіювати посилання');
            }
        });
    });
});