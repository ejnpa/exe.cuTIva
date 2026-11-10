/**
 * Utilitário de segurança contra XSS
 */
const escapeHtml = (value) => 
    String(value || '').replace(/[&<>'"]/g, char => ({ 
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' 
    }[char]));

const state = {
    notes: [],
    activeNote: null,
    adaptedBlobUrl: null,
    currentView: 'original'
};

let currentAbortController = null;

function abortInclusiveRequest(){
    if (currentAbortController){
        currentAbortController.abort();
        currentAbortController = null;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadNotes();

    // Fechar o modal ao clicar fora da caixa de conteúdo
    const modal = document.getElementById('modal-inclusivo');
    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeModal();
            }
        });
    }

    // Fechar o modal com a tecla Escape
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            const m = document.getElementById('modal-inclusivo');
            if (m && !m.hasAttribute('hidden')) {
                closeModal();
            }
        }
    });
});

/**
 * Carrega a lista de apontamentos do utilizador
 */
async function loadNotes() {
    const grid = document.getElementById('grelha-meus-apontamentos');
    if (!grid) return;

    try {
        state.notes = await notesService.getall();
        if (!state.notes.length) {
            grid.innerHTML = `
                <div class="mensagem-vazia">
                    <p data-i18n="pesquisa-vazia">Ainda não partilhaste apontamentos.</p>
                    <a href="/upload.html" data-i18n="upload-titulo">Partilhar o primeiro →</a>
                </div>`;
            if (window.AppLanguage) window.AppLanguage.applyToHTML();
            return; 
        }

        grid.innerHTML = state.notes.map(note => {
            const likeCount = note.likes || 0;
            const isLikedClass = note.liked_by_user ? 'is-liked' : '';
            const noteId = String(note.id);
            const titleSafe = escapeHtml(note.title);
            const subjectSafe = escapeHtml(note.subject || 'Apontamento');
            const authorSafe = escapeHtml(note.author || 'Eu');
            const thumbSafe = escapeHtml(note.thumbnail_url || 'https://via.placeholder.com/300x180?text=PDF');

            return `
            <article class="card-estudo" data-id="${noteId}">
                <div class="capa" 
                     role="button" 
                     tabindex="0"
                     onclick="openDocumentModal('${noteId}', 'original')"
                     onkeydown="if(event.key === 'Enter') openDocumentModal('${noteId}', 'original')"
                     title="Clica para abrir ${titleSafe}">
                    <img src="${thumbSafe}" alt="Pré-visualização de ${titleSafe}">
                    <span class="badge-formato">PDF</span>
                </div>
                
                <div class="info">
                    <span class="tag">${subjectSafe}</span>
                    <h3 onclick="openDocumentModal('${noteId}', 'original')" style="cursor: pointer;" title="Clica para abrir ${titleSafe}">${titleSafe}</h3>
                    <p class="autor">👤 ${authorSafe}</p>
                    
                    <!-- Botões Principais de Ação: Visualização & Resumo Inclusivo -->
                    <div class="card-acoes-principais">
                        <button type="button" class="btn-card-action btn-ver-doc" onclick="openDocumentModal('${noteId}', 'original')" title="Ver documento original">
                            <span>📄</span> <span data-i18n="btn-visualizar">Visualizar</span>
                        </button>
                        <button type="button" class="btn-card-action btn-resumo-inc" onclick="openDocumentModal('${noteId}', 'inclusive')" title="Abrir com adaptação inclusiva (PHDA)">
                            <span>🧠</span> <span data-i18n="btn-resumo-inclusivo">Resumo Inclusivo</span>
                        </button>
                    </div>

                    <!-- Linha Secundária: Gostos e Apagar -->
                    <div class="card-acoes-secundarias">
                        <button type="button" class="btn-like ${isLikedClass}" onclick="toggleLike(this, '${noteId}')" title="Gostar">
                            <svg viewBox="0 0 24 24">
                                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                            </svg>
                            <span class="like-count">${likeCount}</span>
                        </button>

                        <button type="button" onclick="deleteNote('${noteId}')" class="btn-apagar-nota" title="Remover este apontamento">
                            <span class="icone-lixo">🗑️</span> <span data-i18n="btn-apagar">Apagar</span>
                        </button>
                    </div>
                </div>
            </article>`;
        }).join('');

        if (window.AppLanguage) {
            window.AppLanguage.applyToHTML();
        }

    } catch (error) {
        console.error("Erro a carregar apontamentos", error);
        grid.innerHTML = `<p class="loading-state error-state">Erro: ${escapeHtml(error.message)}</p>`;
    }
}

/**
 * Remove um apontamento
 */
async function deleteNote(id) {
    if (!confirm('Tens a certeza que queres apagar este apontamento?')) return;
    try {
        await notesService.delete(id);
        if (typeof showAlerts === 'function') showAlerts('Apontamento apagado com sucesso!', 'sucesso');
        loadNotes();
    } catch (error) {
        console.error("Erro ao apagar:", error);
        if (typeof showAlerts === 'function') showAlerts('Erro de comunicação com o servidor.', 'erro');
    }     
}

/**
 * Abre o modal e inicializa o visualizador com o ficheiro original ou versão inclusiva
 */
async function openDocumentModal(id, viewMode = 'original') {
    const note = state.notes.find(n => String(n.id) === String(id));
    if (!note) {
        console.error("Apontamento não localizado:", id);
        return;
    } 

    abortInclusiveRequest();

    state.activeNote = note;
    

    if (state.adaptedBlobUrl) {
         URL.revokeObjectURL(state.adaptedBlobUrl);
         state.adaptedBlobUrl = null;
    }

    state.currentView = viewMode === 'inclusive' ? 'adapted' : 'original';

    const modal = document.getElementById('modal-inclusivo');
    const titulo = document.getElementById('modal-titulo');
    const audioContainer = document.getElementById('container-audio-player');
    const playerAudio = document.getElementById('player-audio-tts');
    const btnTTS = document.getElementById('btn-gerar-tts');
    
    if (titulo) titulo.textContent = note.title;
    if (audioContainer) audioContainer.style.display = 'none';
    if (playerAudio) {
        playerAudio.pause();
        playerAudio.src = '';
    }
    if (btnTTS) btnTTS.classList.remove('is-active');
    
    if (modal) {
        modal.removeAttribute('hidden');
        document.body.classList.add('modal-open');
    }

    if (viewMode === 'inclusive') {
        generateInclusiveVersion();
    } else {
        showOriginalNote();
    }
}

/**
 * Fecha o modal e limpa recursos
 */
function closeModal() {
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }

    const modal = document.getElementById('modal-inclusivo');
    const iframe = document.getElementById('visualizador-pdf');
    const playerAudio = document.getElementById('player-audio-tts');
    const audioContainer = document.getElementById('container-audio-player');
    const btnTTS = document.getElementById('btn-gerar-tts');

    if (playerAudio) {
        playerAudio.pause();
        playerAudio.src = '';
    }
    if (iframe) iframe.src = '';
    if (audioContainer) audioContainer.style.display = 'none';
    if (btnTTS) btnTTS.classList.remove('is-active');
    
    if (state.adaptedBlobUrl) {
        URL.revokeObjectURL(state.adaptedBlobUrl);
        state.adaptedBlobUrl = null;
    }

    state.activeNote = null;
    if (modal) {
        modal.setAttribute('hidden', '');
        document.body.classList.remove('modal-open');
    }
}

/**
 * Mostra o apontamento original diretamente no visualizador
 */
function showOriginalNote() {
    if (!state.activeNote) return;

    abortInclusiveRequest()

    state.currentView = 'original';

    const iframe = document.getElementById('visualizador-pdf');
    const loadingContainer = document.getElementById('modal-loading-state');
    const btnOriginal = document.getElementById('btn-ver-original');
    const btnInclusao = document.getElementById('btn-gerar-inclusao');

    if (btnOriginal) btnOriginal.classList.add('is-active');
    if (btnInclusao) btnInclusao.classList.remove('is-active');
    if (loadingContainer) loadingContainer.style.display = 'none';

    if (iframe) {
        iframe.src = state.activeNote.file_url;
        iframe.style.display = 'block';
    }
}

/**
 * Processa e gera a versão inclusiva (IA / PHDA)
 */
async function generateInclusiveVersion() {
    if (!state.activeNote) return;

    const note = state.activeNote;

    state.currentView = 'adapted';

    const iframe = document.getElementById('visualizador-pdf');
    const loadingContainer = document.getElementById('modal-loading-state');
    const btnInclusao = document.getElementById('btn-gerar-inclusao');
    const btnOriginal = document.getElementById('btn-ver-original');

    if (btnInclusao) btnInclusao.classList.add('is-active');
    if (btnOriginal) btnOriginal.classList.remove('is-active');

    // Se já foi gerado nesta sessão, reutiliza de imediato
    if (state.adaptedBlobUrl) {
        if (iframe) {
            iframe.src = state.adaptedBlobUrl;
            iframe.style.display = 'block';
        }
        if (loadingContainer) loadingContainer.style.display = 'none';
        return;
    }

    if (iframe) iframe.style.display = 'none';
    if (loadingContainer) {
        const titleText = window.AppLanguage ? window.AppLanguage.get('modal-ia-processando') : '🧠 A processar com Inteligência Artificial...';
        const descText = window.AppLanguage ? window.AppLanguage.get('modal-ia-descricao') : 'A ler, resumir e a estruturar o documento para PHDA.<br>Isto pode demorar cerca de 1 minuto.';

        loadingContainer.innerHTML = `
            <div class="loading-ia-spinner"></div>
            <h3 class="loading-ia-title">${titleText}</h3>
            <p class="loading-ia-desc">${descText}</p>
        `;
        loadingContainer.style.display = 'flex';
    }

    abortInclusiveRequest();

    const controller = new AbortController();
    currentAbortController = controller;

    try {
        const blob = await notesService.adapt(state.activeNote.id, controller.signal);

        if (controller.signal.aborted || state.activeNote !== note || state.currentView !== 'adapted') return;


        state.adaptedBlobUrl = URL.createObjectURL(blob);

        if (iframe) {
            iframe.src = state.adaptedBlobUrl;
            iframe.style.display = 'block';
        }
        if (loadingContainer) loadingContainer.style.display = 'none';
    } catch (error) {
        if (error.name === 'AbortError') return;
        console.error("Erro ao gerar inclusão:", error);
        if (loadingContainer) {
            loadingContainer.innerHTML = `
                <div style="font-size: 38px; margin-bottom: 12px;">⚠️</div>
                <h3 class="loading-ia-title" style="color: #b71c1c;">Erro no processamento</h3>
                <p class="loading-ia-desc" style="color: #721c24; margin-bottom: 18px;">${escapeHtml(error.message)}</p>
                <button type="button" class="btn-card-action btn-ver-doc" onclick="showOriginalNote()">Voltar ao documento original</button>
            `;
        }
    } finally {
        if (currentAbortController === controller) {
            currentAbortController = null;
        }
    }
}

/**
 * Função utilitária para parar e ocultar o leitor de áudio
 */
function stopAudioPlayer(){
    const audioContainer = document.getElementById('container-audio-player');
    const playerAudio = document.getElementById('player-audio-tts');
    const btnTTS = document.getElementById('btn-gerar-tts');

    if(playerAudio){
        playerAudio.pause();
        playerAudio.removeAttribute('src');
        playerAudio.load();
    }
    if (audioContainer){
        audioContainer.style.display = 'none';
    }
    if (btnTTS) {
        btnTTS.classList.remove('is-active');
        btnTTS.setAttribute('aria-pressed', 'false');
    }  
}

/**
 * Atualiza o texto descritivo do botão TTS consoante o separador ativo
 */
function updateTTSButtonLabel(){
    const btnTTS = document.getElementById('btn-gerar-tts');
    if (!btnTTS) return; 
    const textMode = state.currentView === 'adapted' ? 'Resumo Inclusivo' : 'Original';
    btnTTS.title = `Ouvir Leitura em voz altado documento (${textMode})`;
}


/**
 * Alterna e controla a reprodução do sintetizador de voz (TTS)
 */
async function toggleTTSAudio() {
    if (!state.activeNote) return;

    const audioContainer = document.getElementById('container-audio-player');
    const playerAudio = document.getElementById('player-audio-tts');
    const btnTTS = document.getElementById('btn-gerar-tts');

    if (!audioContainer || !playerAudio) return;

    if (audioContainer.style.display === 'flex') {
        playerAudio.pause();
        audioContainer.style.display = 'none';
        if (btnTTS) btnTTS.classList.remove('is-active');
        return;
    }

    const originalContent = btnTTS ? btnTTS.innerHTML : '';
    if (btnTTS) {
        btnTTS.disabled = true;
        btnTTS.innerHTML = '<span class="btn-toolbar-icon">⏳</span> <span>A preparar áudio...</span>';
    }
    
    try {
        const targetUrl = notesService.getAudioUrl(state.activeNote.id, state.currentView);
        playerAudio.src = targetUrl;
        audioContainer.style.display = 'flex';
        if (btnTTS){
            btnTTS.classList.add('is-active');
            btnTTS.setAttribute('aria-pressed', 'true');
        }
        await playerAudio.play().catch(err => {
            console.warn("Reprodução automática bloqueada pelo navegador ou áudio ainda em síntese:", err);
        });
    } catch (error) {
        console.error("Erro ao carregar áudio:", error);
        alert("Não foi possível carregar a síntese de voz para a visualização atual.");
        stopAudioPlayer();
        if (typeof showAlerts === 'function') {
            showAlerts("Não foi possível carregar o áudio para este apontamento.", "erro");
        }
    } finally {
        if (btnTTS) {
            btnTTS.disabled = false;
            btnTTS.innerHTML = originalContent;  
        }
    }
}


