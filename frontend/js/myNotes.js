const myNotesState = {
    myNotes: []
};

function escapeHtml(value){
    return String(value ?? '').replace(/[&<>'"]/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[char]));
}
document.addEventListener('DOMContentLoaded', () => {
    const grid =  document.getElementById('grelha-meus-apontamentos');
    if (!grid) return;
    grid.addEventListener('click', handleCardAction);
    loadMyNotes();
});

async function loadMyNotes(){
    const grid = document.getElementById('grelha-meus-apontamentos');
    try{
        myNotesState.notes = await notesService.getAll();
        renderMyNotes(grid);
    }catch(error){
        console.error('Erro ao carregar apontamentos:', error);
        grid.innerHTML ='<p class="loading-state error-state">Não foi possível carregar os teus apontamentos.</p>';
    }

}

function renderMyNotes(grid){
    if (myNotesState.notes.length === 0) {
        const txtVazia = window.AppLanguage ? window.AppLanguage.get('pesquisa-vazia'):'Ainda nã tenns apontamentos partilhados' ;
        const txtUpload = window.AppLanguage ? window.AppLanguage.get('upload-primeiro'):'Partilhar o primeiro →';

        grid.innerHTML =
            `
            <div class="mensagem-vazia">
                <p>${txtVazia}</p>
                <a href="upload.html">${txtUpload}</a>
            </div>
        `;
        return;
    }
    const labelDelete = window.AppLanguage ? window.AppLanguage.get('btn-apagar'):'Eliminar';
    grid.innerHTML = myNotesState.notes.map(note => {
        const id = escapeHtml(note.id);
        const detailUrl = `noteDetails.html?id=${encodeURIComponent(note.id)}`;
        const thumbnail = escapeHtml(note.thumbnail_url || 'https://via.placeholder.com/300x180?text=PDF');
        const subjectSafe = escapeHtml(note.subject || 'Apontamento');
        const titleSafe = escapeHtml(note.title);
        return `
        <article class="card-estudo" data-id="${id}">
                <a class="capa" href="${detailUrl}">
                    <img src="${thumbnail}" alt="Pré-visualização de ${titleSafe}">
                </a>
                <div class="info">
                    <span class="tag">${subjectSafe}</span>
                    <h2><a href="${detailUrl}" style="text-decoration:none; color:inherit;">${titleSafe}</a></h2>
                    
                    <div class="card-acoes-secundarias" style="display:flex; justify-content:space-between; margin-top:15px; border-top: 1px solid #eee; padding-top:10px;">
                        <button type="button" data-action="like" data-note-id="${id}" class="btn-like ${note.liked_by_user ? 'is-liked' : ''}">
                            <svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                            <span class="like-count">${note.likes || 0}</span>
                        </button>
                        <button type="button" data-action="delete" data-note-id="${id}" class="btn-apagar-nota">
                            <span class="icone-lixo">🗑️</span> ${labelApagar}
                        </button>
                    </div>
                </div>
            </article>
        `;
    }).join('');
}

async function handleCardAction(event) {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const noteId = button.dataset.noteId;
    if (button.dataset.action === 'like') {
        if (typeof window.toggleNoteLike === 'function'){
            await toggleNoteLike(button, noteId);
        }
    } else if (button.dataset.action === 'delete') {
        await deleteMyNote(noteId);
    }
}

async function toggleNoteLike(button, noteId){
    const note = myNotesState.notes.find(item => String(item.id) === String(noteId));

    if (!note || button.disabled) return;

    button.disabled = true;

    try{
        const result = await notesService.setLike(noteId, !note.liked_by_user);

        note.liked_by_user = result.liked;
        note.likes = result.likes_count;

        button.classList.toggle('is-liked', result.liked);
        button.setAttribute('aria-pressed', String(result.liked));

        const count = button.querySelector('.like-count');
        if (count) count.textContent = String(result.likes_count);


    }catch (error){
        console.error('Erro ao atualizar gosto:', error);
        window.showAlerts?.('Não foi possível atualizar o gosto.', 'erro');
    }finally{
        button.disabled = false;
    }
}

async function deleteMyNote(noteId){
    if (!window.confirm('Tem certeza que deseja apagar essa nota?')) return;
    try{
        await notesService.delete(noteId);
        myNotesState.notes = myNotesState.notes.filter(note => String(note.id) !== String(noteId));
        renderMyNotes(document.getElementById('grelha-meus-apontamentos'));
        window.showAlerts?.('Apontamento apagado com sucesso.', 'sucesso');
    }catch (error){
        console.error('Erro ao apagar nota:', error);
        window.showAlerts?.('Não foi possível apagar apontamento.', 'erro');
    }
}
