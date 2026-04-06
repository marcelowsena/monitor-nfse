export interface INfsePendentesProps {
    workerUrl: string;
    apiToken: string;
    exibirLancadas: boolean;
    userDisplayName: string;
}
export interface INfseItem {
    chave: string;
    obra: string;
    numero: string;
    data_emissao: string;
    nome_prest: string;
    cnpj_prest: string;
    valor: number;
    has_pdf?: boolean;
    numero_titulo?: number;
    tipo?: 'nfse' | 'nfe';
}
export interface IObra {
    key: string;
    nome: string;
    regiao?: string;
    pendentes: INfseItem[];
    lancadas: INfseItem[];
}
//# sourceMappingURL=INfsePendentesProps.d.ts.map