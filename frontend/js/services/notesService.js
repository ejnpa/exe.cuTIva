/**
 * NotesService - Service Layer Pattern
 * Responsável exclusiva pela comunicação HTTP com a API.
 */
const notesService = {
    async getall(){
        const response = await fetch(`${API_BASE_URL}/notes/me`, { credentials: 'include'});
        if (!response.ok) throw new Error('Não foi possível carregar os teus apontamentos.');
        return response.json();
    },

    async adapt(noteId, signal){
        const response = await fetch(`${API_BASE_URL}/notes/${noteId}/adapt`, {
             method: 'GET', 
             credentials: 'include',
             signal
        });
        if (!response.ok) throw new Error('Não foi possível gerar a versão inclusiva.');
        return response.blob();
    },

    getAudioUrl(noteId, type = 'original'){
        return `${API_BASE_URL}/notes/${noteId}/audio?type=${encodeURIComponent(type)}`;
    },

    async setLike(noteId, liked){
        const response = await fetch(`${API_BASE_URL}/notes/${noteId}/like`, {
            method: liked?'POST':'DELETE',
            credentials: 'include'
        });
        if (!response.ok) throw new Error('Erro ao registar o gosto.');
        return response.json();
    },

    async delete(noteId){
        const response = await fetch(`${API_BASE_URL}/notes/${noteId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        if (!response.ok) throw new Error('Falha ao remover o apontamento.');
        return response.ok;
    },

    async saveArtifact(noteId, kind, variant ){
    const response = await fetch(`${API_BASE_URL}/library/save`, {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json' },
        body: JSON.stringify({note_id: noteId, kind, variant})
    });

    if (!response.ok) throw new Error('Não foi possível guardar na biblioteca.');

    return response.json();
}   

};

