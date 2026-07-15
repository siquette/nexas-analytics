/**
 * js/state.js — State global compartilhado entre todas as abas.
 *
 * Qualquer aba que precisar dos filtros importa daqui.
 * Quando o usuário muda de aba, os filtros persistem.
 */

const NexasState = {
    // Filtros principais
    onda: null,
    assunto: null,
    pergunta: null,
    categoria_coluna: null,
    direcao: null,

    // Configurações do dendrograma
    nodeYSpacing: 26,
    nodeXSpacing: 220,
    zoomLevel: 1,
    agregacao: 'weighted_mean',

    // Dados carregados
    treeData: null,

    // Callbacks registrados pelas abas
    _listeners: [],

    /**
     * Atualiza um campo do state e notifica os listeners.
     */
    set(key, value) {
        this[key] = value;
        this._notify(key, value);
    },

    /**
     * Registra um callback para quando o state mudar.
     */
    onChange(fn) {
        this._listeners.push(fn);
    },

    _notify(key, value) {
        this._listeners.forEach(fn => fn(key, value));
    },

    /**
     * Serializa os filtros ativos para URLSearchParams.
     */
    toParams() {
        const params = new URLSearchParams();
        if (this.onda) params.set('onda', this.onda);
        if (this.assunto) params.set('assunto', this.assunto);
        if (this.pergunta) params.set('pergunta', this.pergunta);
        if (this.categoria_coluna) params.set('categoria_coluna', this.categoria_coluna);
        if (this.direcao) params.set('direcao', this.direcao);
        return params;
    },

    /**
     * Restaura filtros da URL atual.
     */
    fromURL() {
        const params = new URLSearchParams(window.location.search);
        if (params.get('onda')) this.onda = params.get('onda');
        if (params.get('assunto')) this.assunto = params.get('assunto');
        if (params.get('pergunta')) this.pergunta = params.get('pergunta');
        if (params.get('direcao')) this.direcao = params.get('direcao');
    },

    /**
     * Atualiza a URL sem recarregar a página.
     */
    pushURL() {
        const params = this.toParams();
        window.history.replaceState({}, '', `?${params.toString()}`);
    },

    /**
     * Retorna true se os filtros mínimos estão preenchidos.
     */
    isReady() {
        return !!(this.onda && this.assunto && this.pergunta);
    }
};
