function renderHeader() {
    if (!localStorage.getItem('user')) {
        return `
    <header class="home-header">
        <!-- Podes colar aqui todo o teu bloco <div class="header-start">... -->
        <header class="home-header">
        <div class="header-start">
            <button class="hamburger-button" id="hamburger-button" type="button" aria-label="Abrir menu" aria-expanded="false" aria-controls="side-menu">
                <span></span><span></span><span></span>
            </button>
            <a class="home-brand" href="../html/index.html" aria-label="exe.cuTIva, página inicial">
                <span class="brand-mark">e.</span><span>exe.cuTIva</span>
            </a>
        </div>
        <nav class="home-nav" aria-label="Navegação principal">
            <a href="../html/subjects.html" data-i18n="menu-explorar">Explorar</a>
            <a href="../html/index.html#como-funciona" data-i18n="menu-como-funciona">Como funciona</a>
            <a href="../html/contacts.html" data-i18n="menu-contactos">Contactos</a>
        </nav>
        <div class="header-actions">
            <!-- 1. Área de Autenticação -->
            <div class="home-auth" id="area-auth">
                <a class="home-login" href="login.html" data-i18n="btn-entrar">Entrar</a>
                <a class="home-signup" href="register.html" data-i18n="btn-criar-conta">Criar conta</a>
            </div>

            <!-- 2. Seletor de Idioma -->
            <div class="language-picker">
                <button class="language-toggle" id="language-toggle" type="button" aria-expanded="false" aria-controls="language-menu">
                    <span class="language-globe" aria-hidden="true">🌐</span><span id="selected-language">PT</span><span class="language-chevron" aria-hidden="true">▾</span>
                </button>
                <div class="language-menu" id="language-menu" role="menu">
                    <button type="button" class="language-option is-selected" data-language="pt-PT" data-label="PT" role="menuitem">
                        <div class="lang-info">
                            <span class="lang-flag">🇵🇹</span>
                            <span>Português</span>
                        </div>
                        <small>PT</small>
                    </button>
                    <button type="button" class="language-option" data-language="en" data-label="EN" role="menuitem">
                        <div class="lang-info">
                            <span class="lang-flag">🇬🇧</span>
                            <span>English</span>
                        </div>
                        <small>EN</small>
                    </button>
                </div>
            </div>
        </div>
    </header>
        <!-- Garante que a barra de pesquisa ou links estão atualizados -->
    <div class="menu-backdrop" id="menu-backdrop"></div>
    <aside class="side-menu" id="side-menu">
        <!-- O teu menu lateral aqui -->
        <div class="menu-backdrop" id="menu-backdrop"></div>
    <aside class="side-menu" id="side-menu" aria-label="Menu principal">
        <div class="side-menu-top">
            <span class="side-menu-title" data-i18n="menu-titulo">Menu</span>
            <button class="close-menu" id="close-menu" type="button" aria-label="Fechar menu">✕</button>
        </div>
        <nav class="side-menu-links">
            <a href="../html/index.html"><span class="side-menu-icon">🏠</span> <span data-i18n="menu-lateral-inicio">Página inicial</span></a>
            <a href="../html/subjects.html"><span class="side-menu-icon">📚</span> <span data-i18n="menu-lateral-explorar">Explorar materiais</span></a>
            <a href="../html/upload.html"><span class="side-menu-icon">⬆️</span> <span data-i18n="menu-lateral-partilhar">Partilhar apontamentos</span></a>
            <a href="../html/myNotes.html"><span class="side-menu-icon">📂</span> <span data-i18n="menu-lateral-meus">Os meus apontamentos</span></a>
            <a href="../html/contacts.html"><span class="side-menu-icon">✉️</span> <span data-i18n="menu-contactos">Contactos</span></a>
        </nav>
        <div class="side-menu-bottom">
            <p data-i18n="menu-slogan">Aprende. Partilha. Cresce.</p>
            <a href="../html/register.html"><span data-i18n="btn-conta-gratis">Criar conta gratuita</span> <span>→</span></a>
        </div>
    </aside>
    </aside>
    `;
    }
}

function renderFooter() {
    return `
    <footer class="app-footer">
        <a class="app-brand" href="../html/index.html"><span>e.</span>exe.cuTIva</a>
        <p data-i18n="footer-slogan">Estudar melhor começa por partilhar.</p>
        <small>© 2026 exe.cuTIva</small>
    </footer>
    `;
}

document.addEventListener('DOMContentLoaded', () => {
    document.body.insertAdjacentHTML('afterbegin', renderHeader());
    document.body.insertAdjacentHTML('beforeend', renderFooter());
});