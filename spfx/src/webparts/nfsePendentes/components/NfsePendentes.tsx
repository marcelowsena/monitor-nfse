import * as React from 'react';
import { INfsePendentesProps, IObra } from './INfsePendentesProps';
import styles from './NfsePendentes.module.scss';

interface IState {
  obras:      IObra[];
  carregando: boolean;
  erro:       string;
  ultimaAtt:  string;
}

export default class NfsePendentes extends React.Component<INfsePendentesProps, IState> {

  constructor(props: INfsePendentesProps) {
    super(props);
    this.state = { obras: [], carregando: true, erro: '', ultimaAtt: '' };
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

  // ──────────────────────────────────────────
  // Busca dados do Cloudflare Worker
  // ──────────────────────────────────────────

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

      // Resposta: [{key, nome, pendentes: [{chave, numero, data_emissao, nome_prest, cnpj_prest, valor}]}]
      const dados: IObra[] = await resp.json();

      const obras = dados
        .filter(o => this.props.exibirLancadas || o.pendentes.length > 0)
        .sort((a, b) => a.key.localeCompare(b.key));

      this.setState({
        obras,
        carregando: false,
        ultimaAtt: new Date().toLocaleString('pt-BR'),
      });

    } catch (e: any) {
      this.setState({ carregando: false, erro: e.message || String(e) });
    }
  }

  // ──────────────────────────────────────────
  // Render
  // ──────────────────────────────────────────

  public render(): React.ReactElement {
    const { carregando, erro, obras, ultimaAtt } = this.state;
    const { exibirLancadas } = this.props;

    const totalPendentes = obras.reduce((s, o) => s + o.pendentes.length, 0);

    return (
      <div className={styles.container}>

        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <span className={styles.titulo}>Monitor NFS-e</span>
            <span className={styles.subtitulo}>Notas recebidas no SEFAZ não lançadas no Sienge</span>
          </div>
          <div className={styles.headerRight}>
            {!carregando && (
              <span className={totalPendentes > 0 ? styles.badgePendente : styles.badgeOk}>
                {totalPendentes > 0 ? `${totalPendentes} pendente(s)` : 'Tudo lançado'}
              </span>
            )}
            <button className={styles.btnAtualizar} onClick={() => this._carregarDados()}>
              Atualizar
            </button>
          </div>
        </div>

        {carregando && <div className={styles.loading}>Carregando dados...</div>}

        {erro && (
          <div className={styles.erro}>
            <strong>Erro ao carregar dados:</strong><br />{erro}
          </div>
        )}

        {!carregando && !erro && obras.length === 0 && (
          <div className={styles.vazio}>
            {exibirLancadas
              ? 'Nenhuma nota encontrada.'
              : 'Nenhuma nota pendente de lançamento.'}
          </div>
        )}

        {!carregando && obras.map(obra => this._renderObra(obra))}

        {ultimaAtt && (
          <div className={styles.rodape}>
            Atualizado em: {ultimaAtt} &nbsp;|&nbsp; Fonte: SEFAZ ADN Nacional
          </div>
        )}
      </div>
    );
  }

  private _renderObra(obra: IObra): React.ReactElement {
    const pendentes  = obra.pendentes;
    const totalValor = pendentes.reduce((s, n) => s + (n.valor || 0), 0);

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
                <th>Data Emissão</th>
                <th>Nº NFS-e</th>
                <th>Prestador</th>
                <th>CNPJ</th>
                <th className={styles.direita}>Valor (R$)</th>
              </tr>
            </thead>
            <tbody>
              {pendentes.map((nota, i) => (
                <tr key={nota.chave || i}>
                  <td>{this._formatarData(nota.data_emissao)}</td>
                  <td className={styles.mono}>{nota.numero}</td>
                  <td>{nota.nome_prest}</td>
                  <td className={styles.mono}>{this._formatarCNPJ(nota.cnpj_prest)}</td>
                  <td className={styles.direita}>{this._formatarValor(nota.valor)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={4} className={styles.totalLabel}>TOTAL PENDENTE</td>
                <td className={`${styles.direita} ${styles.totalValor}`}>
                  {this._formatarValor(totalValor)}
                </td>
              </tr>
            </tfoot>
          </table>
        )}

        {pendentes.length === 0 && (
          <div className={styles.semPendentes}>
            Todas as notas desta obra estão lançadas no Sienge.
          </div>
        )}
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
