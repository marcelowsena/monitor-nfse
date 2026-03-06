export interface INfsePendentesProps {
  workerUrl:       string;   // URL do Cloudflare Worker
  apiToken:        string;   // Token de leitura (CF_API_TOKEN)
  exibirLancadas:  boolean;
  userDisplayName: string;
}

export interface INfseItem {
  chave:        string;
  obra:         string;
  numero:       string;
  data_emissao: string;
  nome_prest:   string;
  cnpj_prest:   string;
  valor:        number;
}

export interface IObra {
  key:       string;
  nome:      string;
  pendentes: INfseItem[];
}
