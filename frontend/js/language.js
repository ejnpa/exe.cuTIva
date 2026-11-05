class LanguageManager {
    constructor() {
        if (LanguageManager.instance) {
            return LanguageManager.instance;
        }

        let savedLang = localStorage.getItem('preferred_language');

        if (!savedLang || savedLang === 'null' || savedLang === 'undefined') {
            savedLang = 'pt-PT';
            localStorage.setItem('preferred_language', 'pt-PT');
        }

        this.currentLang = savedLang;

        this.dictionary = { };
        LanguageManager.instance = this;
    }

    async loadDictionary(){
        try{
            const response = await fetch(`locales/${this.currentLang}.json`);
            this.dictionary = await response.json();
            this.applyToHTML();
        }catch(error){
            console.error("Erro ao carregar ficheiro de idioma:", error)
        };
    };

    async setLanguage(lang) {
        
        this.currentLang = lang;
        localStorage.setItem('preferred_language', lang);
        this.loadDictionary();
        
    }

    get(key) {
        return this.dictionary[key] || key;
    }

    applyToHTML() {
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const languageStr = this.get(key);

            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                element.placeholder = languageStr;
            } else {
                element.innerHTML = languageStr;
            }
        });
    }
}

window.AppLanguage = new LanguageManager();
window.AppLanguage.loadDictionary();

console.log("✅ Dicionário carregado! Idioma atual:", window.AppLanguage.currentLang);