function getCurrentUser() {
    return localStorage.getItem('user');
}

async function logout() {
    try {
        await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
    } finally {
        localStorage.removeItem('user');
        window.location.href = 'index.html';
    }
}

function renderAuthArea() {
    const area = document.getElementById('area-auth');
    if (!area) return;
    
    const user = getCurrentUser();
    
    // As etiquetas data-i18n agora vêm embutidas no código injetado!
    area.innerHTML = user
        ? `<a class="home-login" href="myNotes.html" data-i18n="menu-lateral-meus">Os meus apontamentos</a>
           <a class="home-signup" href="upload.html" data-i18n="upload-titulo">Partilhar material</a>
           <button class="auth-logout home-login" style="background:none; border:none; cursor:pointer;" type="button" data-i18n="btn-sair">Sair</button>`
        : `<a class="home-login" href="login.html" data-i18n="btn-entrar">Entrar</a>
           <a class="home-signup" href="register.html" data-i18n="btn-criar-conta">Criar conta</a>`;
           
    area.querySelector('.auth-logout')?.addEventListener('click', logout);
    
    // Pede ao dicionário global para traduzir estes botões novos de imediato
    if (window.AppLanguage) {
        window.AppLanguage.applyToHTML();
    }
}

function protectPage() {
    if (document.body.dataset.requiresAuth === 'true' && !getCurrentUser()) {
        window.location.href = 'login.html';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    protectPage();
    renderAuthArea();
});