const structureService  = {
    async getStructure(){
        const response = await fetch(`${API_BASE_URL}/notes/structure`);
        if(!response.ok) throw new Error('Não foi possível carregar a estrutura académica.');
        return response.json();
    }
};