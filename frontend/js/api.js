/**
 * js/api.js — Funções de fetch compartilhadas entre todas as abas.
 *
 * Centraliza todas as chamadas à API do backend.
 * Cada função retorna os dados já parseados ou lança erro.
 */

const NexasAPI = {

    async getOndas() {
        const resp = await fetch('/api/ondas');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },

    async getAssuntos(onda) {
        const resp = await fetch(`/api/assuntos?onda=${encodeURIComponent(onda)}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },

    async getPerguntas(onda, assunto) {
        const resp = await fetch(
            `/api/perguntas?onda=${encodeURIComponent(onda)}&assunto=${encodeURIComponent(assunto)}`
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },

    async getCategoriasColuna(onda, assunto, pergunta) {
        const resp = await fetch(
            `/api/filtros/categorias?onda=${encodeURIComponent(onda)}&assunto=${encodeURIComponent(assunto)}&pergunta=${encodeURIComponent(pergunta)}`
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        return data.categorias || data;
    },

    async getTree(params) {
        const resp = await fetch(`/api/tree?${params.toString()}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },

    async getTabela(params) {
        const resp = await fetch(`/api/tabela?${params.toString()}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },

    /**
     * Monta a URL de download e dispara via link oculto.
     */
    downloadTabela(formato, params) {
        const url = `/api/tabela/download/${formato}?${params.toString()}`;
        const link = document.createElement('a');
        link.href = url;
        link.click();
    }
};
