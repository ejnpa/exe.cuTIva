class LanguageManager {
    constructor() {
        if (LanguageManager.instance) {
            return LanguageManager.instance;
        }

        const savedLang = localStorage.getItem('preferred_language');
        this.currentLang = ["pt-PT", "en"].includes(savedLang)?savedLang:'pt-PT';

        localStorage.setItem('preferred_language', this.currentLang);

        this.dictionary = { };
        LanguageManager.instance = this;
    }

    async loadDictionary(){
        try{
            const response = await fetch(
                `locales/${encodeURIComponent(this.currentLang)}.json`
            );

            if (!response.ok) throw new Error(`Erro ao carregar ficheiro de idioma: ${response.status}`);

            this.dictionary = await response.json();
            this.applyToHTML();
        }catch(error){
            console.error("Erro ao carregar ficheiro de idioma:", error)
        }
    };

    async setLanguage(lang) {
        if (!["pt-PT", "en"].includes(lang)) return;
        this.currentLang = lang;
        localStorage.setItem('preferred_language', lang);
        await this.loadDictionary();
        
    }

    get(key) {
        return this.dictionary[key] || key;
    }

    applyToHTML() {
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.get(key);

            if (
                element.tagName === 'INPUT' ||
                element.tagName === 'TEXTAREA'
            ){
                element.placeholder = translation;
            } else {
                element.innerHTML = translation;
            }
        });
    }
}

window.AppLanguage = new LanguageManager();
window.AppLanguage.loadDictionary();
