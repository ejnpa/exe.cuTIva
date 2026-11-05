document.addEventListener('DOMContentLoaded', async function() {
    
    // Apanhamos as caixas
    const selectEscola = document.getElementById('escola');
    const selectCurso = document.getElementById('curso');
    const selectAno = document.getElementById('ano');
    const selectDisciplina = document.getElementById('disciplina');

    // Se alguma das caixas não existir nesta página, o script para sem dar erro
    if (!selectEscola || !selectCurso || !selectAno || !selectDisciplina) return;

    // Função auxiliar para resetar
    function resetDropdown(elemento, textoPadrao) {
        elemento.innerHTML = `<option value="" selected>${textoPadrao}</option>`;
        elemento.disabled = true;
        elemento.style.backgroundColor = "#f9f9f9";
    }

    window.dados_escola_global = {};

    try {
        window.dados_escola_global = await structureService.getStructure();
        Object.keys(window.dados_escola_global).forEach(escola => {
            const op = document.createElement('option');
            op.value = escola; 
            op.textContent = escola;
            selectEscola.appendChild(op);
        }); 
    }catch (error) {
         console.error("Não foi possível carregar a estrutura da escola:", error);
    }
        
    const params = new URLSearchParams(window.location.search);
    const filtro_escola = params.get('escola') || "";
    const filtro_curso = params.get('curso') || "";
    const filtro_ano = params.get('ano') || "";
    const filtro_disciplina = params.get('disciplina') || "";
    
    if (filtro_escola) {
        selectEscola.value = filtro_escola;
        atualizarCursos();
    }


    function atualizarCursos() {
        const escola = selectEscola.value;
        const cursos = window.dados_escola_global[escola];

        resetDropdown(selectCurso, 'Todos os Cursos...');
        resetDropdown(selectAno, 'Todos os Anos...');
        resetDropdown(selectDisciplina, 'Todas as Disciplinas...');
        if (cursos && escola !== "") {
            selectCurso.disabled = false;
            selectCurso.style.backgroundColor = "white";
            Object.keys(cursos).forEach(curso => {
                const op = document.createElement('option');
                op.value = curso; op.textContent = curso;
                if (filtro_curso === curso) op.selected = true;
                selectCurso.appendChild(op);
            });
            atualizarAnos();
        }
    }

    function atualizarAnos() {
        const escola = selectEscola.value;
        const curso = selectCurso.value;
        const anos = window.dados_escola_global[escola]?.[curso];

        resetDropdown(selectAno, 'Todos os Anos...');
        resetDropdown(selectDisciplina, 'Todas as Disciplinas...');

        if (anos && curso !== "") {
            selectAno.disabled = false;
            selectAno.style.backgroundColor = "white";
            Object.keys(anos).forEach(ano => {
                const op = document.createElement('option');
                op.value = ano; op.textContent = ano;
                if(filtro_ano === ano) op.selected = true;
                selectAno.appendChild(op);
            });
            atualizarDisciplinas();
        }
    }

    function atualizarDisciplinas() {

        const escola = selectEscola.value;
        const curso = selectCurso.value;
        const ano = selectAno.value;
        const disciplinas = window.dados_escola_global[escola]?.[curso]?.[ano];

        resetDropdown(selectDisciplina, 'Todas as Disciplinas...');

        if (disciplinas && ano !== "") {
            selectDisciplina.disabled = false;
            selectDisciplina.style.backgroundColor = "white";
            disciplinas.forEach(disciplina => {
                const op = document.createElement('option');
                op.value = disciplina; op.textContent = disciplina;
                if (filtro_disciplina === disciplina) op.selected = true;
                selectDisciplina.appendChild(op);
            });
        }
    }
       
    selectEscola.addEventListener('change', atualizarCursos);
    selectCurso.addEventListener('change', atualizarAnos);
    selectAno.addEventListener('change', atualizarDisciplinas);
}); 
       

        
