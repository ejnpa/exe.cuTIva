document.addEventListener('DOMContentLoaded', () => {
    // 1. MENU LATERAL
    const menuButton = document.getElementById('hamburger-button');
    const closeMenu = document.getElementById('close-menu');
    const sideMenu = document.getElementById('side-menu');
    const backdrop = document.getElementById('menu-backdrop');
    
    if (menuButton && sideMenu) {
        const setMenuState = (isOpen) => {
            sideMenu.classList.toggle('is-open', isOpen);
            backdrop.classList.toggle('is-open', isOpen);
            document.body.classList.toggle('menu-open', isOpen);
            menuButton.setAttribute('aria-expanded', isOpen);
        };

        menuButton.addEventListener('click', () => setMenuState(true));
        if (closeMenu) closeMenu.addEventListener('click', () => setMenuState(false));
        if (backdrop) backdrop.addEventListener('click', () => setMenuState(false));

        document.addEventListener('keydown', event => {
            if (event.key === 'Escape') setMenuState(false);
        });
    }

    // 2. SELETOR DE IDIOMAS
    const toggle = document.getElementById('language-toggle');
    const picker = document.querySelector('.language-picker');
    const label = document.getElementById('selected-language');
        
    if (toggle && picker && label) {
        
        const selectLanguage = (option) => {
            const lang = option.dataset.language;
            document.documentElement.lang = lang;
            label.textContent = option.dataset.label;
            
            document.querySelectorAll('.language-option').forEach(item => 
                item.classList.toggle('is-selected', item === option)
            ); 
            
            
            if (window.AppLanguage) {
                window.AppLanguage.setLanguage(lang);
            } else {
                console.error("ERRO: window.AppLanguage não existe!");
            }
        };

        const savedLanguage = localStorage.getItem('preferred_language') || 'pt-PT';
        const savedOption = document.querySelector(`.language-option[data-language="${savedLanguage}"]`);
        
    
        try {
            if (savedOption) selectLanguage(savedOption);
        } catch (e) {
            console.error("Erro a arrancar o idioma:", e);
        }

        toggle.addEventListener('click', () => {
            const isOpen = picker.classList.toggle('is-open');    
            toggle.setAttribute('aria-expanded', isOpen);    
        });
                   
        document.querySelectorAll('.language-option').forEach(option => {
            option.addEventListener('click', () => {
                selectLanguage(option);
                picker.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
            });
        });    

        document.addEventListener('click', event => {
            if (!picker.contains(event.target)) {
                 picker.classList.remove('is-open'); 
                 toggle.setAttribute('aria-expanded', 'false');
            }
        });
    }
});

// 3. ALERTAS GLOBAIS
window.showAlerts = function(message, type = 'sucesso') {
    let container = document.getElementById('container-alertas-global');
    if (!container) {
        container = document.createElement('div');
        container.id = 'container-alertas-global';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '10px';
        container.style.width = '100%';
        container.style.maxWidth = '350px';
        document.body.appendChild(container);
    }

    const alert = document.createElement('div');
    alert.className = `alerta alerta-${type}`;
    alert.textContent = message;
    container.appendChild(alert);

    setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transition = 'opacity 0.4s';
        setTimeout(() => alert.remove(), 400);
    }, 4000);
};

window.toggleLike = async function (button, noteId) {
    if (!localStorage.getItem('user')){
        const message = window.AppLanguage ? window.AppLanguage.get('erro-login-like'):'';
        window.showAlerts(message, 'erro');
        return;
    }

    const currentlyLiked = button.classList.contains('is-liked');

    try{
        const data = await notesService.setLike(noteId, !currentlyLiked);
        const countSpan = button.querySelector('.like-count');

        button.classList.toggle("is-liked", data.liked);

        if (countSpan && Number.isFinite(Number(data.likes_count))) {
            countSpan.textContent = String(data.likes_count);
        }
    }catch(error){
        console.error("Erro no toggleLike:", error);
        window.showAlerts("Não foi possível atualizar o gosto.",
            "erro");
    }
}
