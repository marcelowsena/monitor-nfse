import * as React from 'react';
import { INfsePendentesProps, IObra } from './INfsePendentesProps';
import styles from './NfsePendentes.module.scss';

type SortDir   = 'asc' | 'desc';
type SortField = 'data_emissao' | 'valor';
type Aba = 'pendentes' | 'lancadas';

interface IState {
  obras:      IObra[];
  carregando: boolean;
  erro:       string;
  ultimaAtt:  string;
  filtro:     string;
  sortField:  SortField;
  sortDir:    SortDir;
  abaAtiva:   Aba;
}

export default class NfsePendentes extends React.Component<INfsePendentesProps, IState> {

  constructor(props: INfsePendentesProps) {
    super(props);
    this.state = { obras: [], carregando: true, erro: '', ultimaAtt: '', filtro: '', sortField: 'data_emissao', sortDir: 'desc', abaAtiva: 'pendentes' };
  }

  public componentDidMount(): void {
    this._carregarDados().catch(console.error);
  }

  public componentDidUpdate(prevProps: INfsePendentesProps): void {
    if (prevProps.workerUrl !== this.props.workerUrl ||
        prevProps.apiToken  !== this.props.apiToken  ||
        prevProps.exibirLancadas !== this.props.exibirLancadas) {
      this._carregarDados().catch(console.error);
    }
  }

  private async _carregarDados(): Promise<void> {
    this.setState({ carregando: true, erro: '' });
    const { workerUrl, apiToken } = this.props;

    if (!workerUrl || !apiToken) {
      this.setState({ carregando: false, erro: 'Configure a URL do Worker e o Token nas propriedades do web part.' });
      return;
    }

    const url = `${workerUrl.replace(/\/$/, '')}/api/pendentes?token=${encodeURIComponent(apiToken)}`;

    try {
      const resp = await fetch(url);
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`Erro ${resp.status}: ${txt.substring(0, 200)}`);
      }

      const dados: IObra[] = await resp.json();

      // Converte valor para número em todas as notas
      const obrasNormalizadas = dados.map(o => ({
        ...o,
        pendentes: (o.pendentes || []).map(n => ({ ...n, valor: this._toFloat(n.valor) })),
        lancadas:  (o.lancadas  || []).map(n => ({ ...n, valor: this._toFloat(n.valor) })),
      }));

      const obras = obrasNormalizadas
        .filter(o => this.props.exibirLancadas || o.pendentes.length > 0)
        .sort((a, b) => a.key.localeCompare(b.key));

      this.setState({ obras, carregando: false, ultimaAtt: new Date().toLocaleString('pt-BR') });

    } catch (e: any) {
      this.setState({ carregando: false, erro: e.message || String(e) });
    }
  }

  // Converte qualquer tipo de valor para float
  // SEFAZ retorna string no formato US "241707.61" (ponto decimal)
  // Formato BR "241.707,61" também é tratado como fallback
  private _toFloat(v: any): number {
    if (typeof v === 'number') return v;
    const s = String(v || '0');
    if (s.includes(',')) {
      // Formato BR: remove separador de milhar (ponto) e troca vírgula por ponto
      return parseFloat(s.replace(/\./g, '').replace(',', '.')) || 0;
    }
    // Formato padrão/US: parseia diretamente
    return parseFloat(s) || 0;
  }

  private _toggleSort(field: SortField): void {
    this.setState(s => ({
      sortField: field,
      sortDir: s.sortField === field && s.sortDir === 'asc' ? 'desc' : 'asc',
    }));
  }

  public render(): React.ReactElement {
    const { carregando, erro, obras, ultimaAtt, filtro, sortField, sortDir, abaAtiva } = this.state;

    const totalPendentes = obras.reduce((s, o) => s + o.pendentes.length, 0);
    const totalLancadas  = obras.reduce((s, o) => s + (o.lancadas || []).length, 0);

    return (
      <div className={styles.container}>

        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <span className={styles.titulo}>Monitor NFS-e</span>
            <span className={styles.subtitulo}>
              {abaAtiva === 'pendentes'
                ? 'Notas recebidas no SEFAZ nao lancadas no Sienge'
                : 'Notas ja lancadas no Sienge'}
            </span>
          </div>
          <div className={styles.headerRight}>
            {!carregando && abaAtiva === 'pendentes' && (
              <span className={totalPendentes > 0 ? styles.badgePendente : styles.badgeOk}>
                {totalPendentes > 0 ? `${totalPendentes} pendente(s)` : 'Tudo lancado'}
              </span>
            )}
            {!carregando && abaAtiva === 'lancadas' && (
              <span className={styles.badgeLancada}>
                {totalLancadas} lancada(s)
              </span>
            )}
            <button className={styles.btnAtualizar} onClick={() => this._carregarDados()}>
              Atualizar
            </button>
          </div>
        </div>

        {/* Abas */}
        {!carregando && !erro && (
          <div className={styles.abas}>
            <button
              className={abaAtiva === 'pendentes' ? styles.abaAtiva : styles.abaInativa}
              onClick={() => this.setState({ abaAtiva: 'pendentes', filtro: '' })}
            >
              Pendentes ({totalPendentes})
            </button>
            <button
              className={abaAtiva === 'lancadas' ? styles.abaAtiva : styles.abaInativa}
              onClick={() => this.setState({ abaAtiva: 'lancadas', filtro: '' })}
            >
              Lancadas ({totalLancadas})
            </button>
          </div>
        )}

        {/* Filtro global */}
        {!carregando && !erro && obras.length > 0 && (
          <div className={styles.filtroBar}>
            <input
              type="text"
              placeholder="Filtrar por data, numero, prestador, CNPJ ou valor..."
              value={filtro}
              onChange={e => this.setState({ filtro: e.target.value })}
              className={styles.filtroInput}
            />
            {filtro && (
              <button className={styles.filtroClear} onClick={() => this.setState({ filtro: '' })}>
                X
              </button>
            )}
          </div>
        )}

        {carregando && <div className={styles.loading}>Carregando dados...</div>}

        {erro && (
          <div className={styles.erro}>
            <strong>Erro ao carregar dados:</strong><br />{erro}
          </div>
        )}

        {!carregando && !erro && abaAtiva === 'pendentes' && obras.length === 0 && (
          <div className={styles.vazio}>Nenhuma nota pendente de lancamento.</div>
        )}

        {!carregando && !erro && abaAtiva === 'lancadas' && totalLancadas === 0 && (
          <div className={styles.vazio}>Nenhuma nota lancada registrada ainda.</div>
        )}

        {!carregando && abaAtiva === 'pendentes' && obras.map(obra => this._renderObra(obra, filtro, sortField, sortDir))}
        {!carregando && abaAtiva === 'lancadas'  && obras.map(obra => this._renderObraLancadas(obra, filtro, sortField, sortDir))}

        {ultimaAtt && (
          <div className={styles.rodape}>
            Atualizado em: {ultimaAtt} &nbsp;|&nbsp; Fonte: SEFAZ ADN Nacional
          </div>
        )}
      </div>
    );
  }

  private _renderObra(obra: IObra, filtro: string, sortField: SortField, sortDir: SortDir): React.ReactElement {
    const termo = filtro.toLowerCase();

    let pendentes = obra.pendentes.filter(n => {
      if (!termo) return true;
      const tipoLabel = n.tipo === 'nfe' ? 'material' : 'servico';
      return (
        this._formatarData(n.data_emissao).includes(termo) ||
        (n.numero || '').toLowerCase().includes(termo) ||
        (n.nome_prest || '').toLowerCase().includes(termo) ||
        this._formatarCNPJ(n.cnpj_prest).includes(termo) ||
        this._formatarValor(n.valor).includes(termo) ||
        tipoLabel.includes(termo)
      );
    });

    pendentes = [...pendentes].sort((a, b) => {
      const cmp = sortField === 'valor'
        ? a.valor - b.valor
        : (a.data_emissao || '').localeCompare(b.data_emissao || '');
      return sortDir === 'asc' ? cmp : -cmp;
    });

    // Esconde a obra se o filtro não retornou nenhuma linha
    if (filtro && pendentes.length === 0) {
      return <div key={obra.key} />;
    }

    const totalValor = pendentes.reduce((s, n) => s + n.valor, 0);
    const setaData  = sortField === 'data_emissao' ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';
    const setaValor = sortField === 'valor'        ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';

    return (
      <div key={obra.key} className={styles.obraCard}>

        <div className={styles.obraHeader}>
          <span className={styles.obraNome}>{obra.nome || obra.key}</span>
          <span className={pendentes.length > 0 ? styles.badgePendente : styles.badgeOk}>
            {pendentes.length > 0 ? `${pendentes.length} pendente(s)` : 'Em dia'}
          </span>
        </div>

        {pendentes.length > 0 && (
          <table className={styles.tabela}>
            <thead>
              <tr>
                <th
                  className={styles.thSortable}
                  onClick={() => this._toggleSort('data_emissao')}
                  title="Clique para ordenar por data"
                >
                  Data Emissao{setaData}
                </th>
                <th>Nr</th>
                <th>Prestador</th>
                <th>CNPJ</th>
                <th>Tipo</th>
                <th
                  className={`${styles.direita} ${styles.thSortable}`}
                  onClick={() => this._toggleSort('valor')}
                  title="Clique para ordenar por valor"
                >
                  Valor (R$){setaValor}
                </th>
                <th style={{width: '60px'}}></th>
              </tr>
            </thead>
            <tbody>
              {pendentes.map((nota, i) => (
                <tr key={nota.chave || i}>
                  <td>{this._formatarData(nota.data_emissao)}</td>
                  <td className={styles.mono}>{nota.numero || '—'}</td>
                  <td title={nota.nome_prest || ''}>{nota.nome_prest || '—'}</td>
                  <td className={styles.mono}>{this._formatarCNPJ(nota.cnpj_prest)}</td>
                  <td>{nota.tipo === 'nfe' ? 'Material' : 'Servico'}</td>
                  <td className={styles.direita}>{this._formatarValor(nota.valor)}</td>
                  <td className={styles.tdPdf}>
                    {nota.has_pdf && (
                      <a
                        href={`${this.props.workerUrl.replace(/\/$/, '')}/api/pdf/${nota.chave}?token=${encodeURIComponent(this.props.apiToken)}`}
                        target="_blank"
                        rel="noreferrer"
                        className={styles.btnPdf}
                        title="Ver DANFSe"
                      >
                        PDF
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={6} className={styles.totalLabel}>TOTAL PENDENTE</td>
                <td className={`${styles.direita} ${styles.totalValor}`}>
                  {this._formatarValor(totalValor)}
                </td>
              </tr>
            </tfoot>
          </table>
        )}

        {pendentes.length === 0 && !filtro && (
          <div className={styles.semPendentes}>
            Todas as notas desta obra estao lancadas no Sienge.
          </div>
        )}
      </div>
    );
  }

  private _renderObraLancadas(obra: IObra, filtro: string, sortField: SortField, sortDir: SortDir): React.ReactElement {
    const termo = filtro.toLowerCase();
    let lancadas = (obra.lancadas || []).filter(n => {
      if (!termo) return true;
      const tipoLabel = n.tipo === 'nfe' ? 'material' : 'servico';
      return (
        this._formatarData(n.data_emissao).includes(termo) ||
        (n.numero || '').toLowerCase().includes(termo) ||
        (n.nome_prest || '').toLowerCase().includes(termo) ||
        this._formatarCNPJ(n.cnpj_prest).includes(termo) ||
        this._formatarValor(n.valor).includes(termo) ||
        tipoLabel.includes(termo)
      );
    });

    lancadas = [...lancadas].sort((a, b) => {
      const cmp = sortField === 'valor'
        ? a.valor - b.valor
        : (a.data_emissao || '').localeCompare(b.data_emissao || '');
      return sortDir === 'asc' ? cmp : -cmp;
    });

    if (lancadas.length === 0) return <div key={obra.key} />;

    const totalValor = lancadas.reduce((s, n) => s + n.valor, 0);
    const setaData  = sortField === 'data_emissao' ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';
    const setaValor = sortField === 'valor'        ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';

    return (
      <div key={obra.key} className={styles.obraCard}>
        <div className={styles.obraHeader}>
          <span className={styles.obraNome}>{obra.nome || obra.key}</span>
          <span className={styles.badgeLancada}>{lancadas.length} lancada(s)</span>
        </div>
        <table className={`${styles.tabela} ${styles.tabelaLancada}`}>
          <thead>
            <tr>
              <th
                className={styles.thSortable}
                onClick={() => this._toggleSort('data_emissao')}
                title="Clique para ordenar por data"
              >
                Data Emissao{setaData}
              </th>
              <th>Nr</th>
              <th>Titulo Sienge</th>
              <th>Prestador</th>
              <th>CNPJ</th>
              <th>Tipo</th>
              <th
                className={`${styles.direita} ${styles.thSortable}`}
                onClick={() => this._toggleSort('valor')}
                title="Clique para ordenar por valor"
              >
                Valor (R$){setaValor}
              </th>
              <th style={{width: '60px'}}></th>
            </tr>
          </thead>
          <tbody>
            {lancadas.map((nota, i) => (
              <tr key={nota.chave || i}>
                <td>{this._formatarData(nota.data_emissao)}</td>
                <td className={styles.mono}>{nota.numero || '—'}</td>
                <td className={styles.mono}>{nota.numero_titulo || '—'}</td>
                <td title={nota.nome_prest || ''}>{nota.nome_prest || '—'}</td>
                <td className={styles.mono}>{this._formatarCNPJ(nota.cnpj_prest)}</td>
                <td>{nota.tipo === 'nfe' ? 'Material' : 'Servico'}</td>
                <td className={styles.direita}>{this._formatarValor(nota.valor)}</td>
                <td className={styles.tdPdf}>
                  {nota.has_pdf && (
                    <a
                      href={`${this.props.workerUrl.replace(/\/$/, '')}/api/pdf/${nota.chave}?token=${encodeURIComponent(this.props.apiToken)}`}
                      target="_blank"
                      rel="noreferrer"
                      className={styles.btnPdf}
                      title="Ver DANFSe"
                    >
                      PDF
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={7} className={styles.totalLabel}>TOTAL LANCADO</td>
              <td className={`${styles.direita} ${styles.totalValorLancada}`}>
                {this._formatarValor(totalValor)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    );
  }

  private _formatarData(s: string): string {
    if (!s) return '—';
    const [ano, mes, dia] = s.split('-');
    return dia && mes && ano ? `${dia}/${mes}/${ano}` : s;
  }

  private _formatarValor(v: number): string {
    return (v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  private _formatarCNPJ(s: string): string {
    const d = (s || '').replace(/\D/g, '');
    if (d.length !== 14) return s || '—';
    return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`;
  }
}
