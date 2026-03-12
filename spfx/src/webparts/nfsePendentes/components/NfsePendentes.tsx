import * as React from 'react';
import { INfsePendentesProps, IObra } from './INfsePendentesProps';
import styles from './NfsePendentes.module.scss';

type SortDir   = 'asc' | 'desc';
type SortField = 'data_emissao' | 'valor';
type Aba = 'pendentes' | 'lancadas' | 'resumo';

interface IState {
  obras:               IObra[];
  carregando:          boolean;
  erro:                string;
  ultimaAtt:           string;
  filtro:              string;
  filtroObra:          string;
  sortField:           SortField;
  sortDir:             SortDir;
  abaAtiva:            Aba;
  filtroResumoObra:  string;
  filtroResumoMeses: string[];
}

export default class NfsePendentes extends React.Component<INfsePendentesProps, IState> {

  constructor(props: INfsePendentesProps) {
    super(props);
    this.state = {
      obras: [], carregando: true, erro: '', ultimaAtt: '', filtro: '', filtroObra: '',
      sortField: 'data_emissao', sortDir: 'desc', abaAtiva: 'pendentes',
      filtroResumoObra: '', filtroResumoMeses: [],
    };
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

  private _toFloat(v: any): number {
    if (typeof v === 'number') return v;
    const s = String(v || '0');
    if (s.includes(',')) {
      return parseFloat(s.replace(/\./g, '').replace(',', '.')) || 0;
    }
    return parseFloat(s) || 0;
  }

  private _toggleSort(field: SortField): void {
    this.setState(s => ({
      sortField: field,
      sortDir: s.sortField === field && s.sortDir === 'asc' ? 'desc' : 'asc',
    }));
  }

  // ── Gráfico SVG ────────────────────────────────────────────────────────────

  private _numCompacto(v: number): string {
    if (v === 0) return '0';
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000)     return `${(v / 1_000).toFixed(0)}k`;
    return v.toFixed(0);
  }

  private _renderBarChart(
    dados:  { label: string; valor: number }[],
    cor:    string,
    fmtY:   (v: number) => string,
  ): React.ReactElement {
    if (dados.length === 0) {
      return <div className={styles.chartVazio}>Sem dados para o periodo selecionado.</div>;
    }

    const VW = 360, VH = 165;
    const pl = 44, pr = 8, pt = 14, pb = 34;
    const cw = VW - pl - pr;
    const ch = VH - pt - pb;

    const maxVal = Math.max(...dados.map(d => d.valor), 1);
    const n      = dados.length;
    const slot   = cw / n;
    const barW   = Math.min(slot * 0.62, 38);
    const nTicks = 4;
    const rotacionar = n > 5;

    return (
      <svg viewBox={`0 0 ${VW} ${VH}`} style={{ width: '100%', height: 'auto' }}>
        {/* Grade e labels eixo Y */}
        {Array.from({ length: nTicks + 1 }, (_, i) => {
          const ratio = i / nTicks;
          const y = pt + ch * (1 - ratio);
          return (
            <g key={i}>
              <line x1={pl} y1={y} x2={pl + cw} y2={y} stroke="#f0f0f0" strokeWidth="1" />
              <text x={pl - 3} y={y + 3} fontSize="8" textAnchor="end" fill="#b0b0b0">
                {fmtY(maxVal * ratio)}
              </text>
            </g>
          );
        })}

        {/* Eixos */}
        <line x1={pl} y1={pt}      x2={pl}      y2={pt + ch} stroke="#ddd" strokeWidth="1" />
        <line x1={pl} y1={pt + ch} x2={pl + cw} y2={pt + ch} stroke="#ddd" strokeWidth="1" />

        {/* Barras */}
        {dados.map((d, i) => {
          const barH = Math.max((d.valor / maxVal) * ch, d.valor > 0 ? 2 : 0);
          const x    = pl + i * slot + (slot - barW) / 2;
          const y    = pt + ch - barH;
          const cx2  = x + barW / 2;
          const ly   = pt + ch + 16;
          return (
            <g key={i}>
              <rect x={x} y={y} width={barW} height={barH} fill={cor} rx="2" opacity="0.85" />
              {d.valor > 0 && barH > 12 && (
                <text x={cx2} y={y - 2} fontSize="7" textAnchor="middle" fill={cor} fontWeight="600">
                  {fmtY(d.valor)}
                </text>
              )}
              <text
                x={cx2} y={ly}
                fontSize="8"
                textAnchor={rotacionar ? 'end' : 'middle'}
                fill="#888"
                transform={rotacionar ? `rotate(-38, ${cx2}, ${ly})` : undefined}
              >
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
    );
  }

  // ── Render principal ────────────────────────────────────────────────────────

  public render(): React.ReactElement {
    const {
      carregando, erro, obras, ultimaAtt, filtro, filtroObra,
      sortField, sortDir, abaAtiva, filtroResumoObra, filtroResumoMeses,
    } = this.state;

    const totalPendentes = obras.reduce((s, o) => s + o.pendentes.length, 0);
    const totalLancadas  = obras.reduce((s, o) => s + (o.lancadas || []).length, 0);

    // ── Dados para aba Resumo ─────────────────────────────────────────────────
    // Meses disponíveis (ordenados decrescente para o dropdown)
    const mesesSet: Record<string, true> = {};
    obras.forEach(o => o.pendentes.forEach(n => {
      const m = (n.data_emissao || '').slice(0, 7);
      if (m.length === 7) mesesSet[m] = true;
    }));
    const mesesDisponiveis = Object.keys(mesesSet).sort().reverse();

    const obrasResumo = obras.filter(o => !filtroResumoObra || o.key === filtroResumoObra);
    const notasResumo = obrasResumo
      .flatMap(o => o.pendentes)
      .filter(n => filtroResumoMeses.length === 0 || filtroResumoMeses.indexOf((n.data_emissao || '').slice(0, 7)) >= 0);

    const totalResumoQtde  = notasResumo.length;
    const totalResumoValor = notasResumo.reduce((s, n) => s + n.valor, 0);
    const totalLancadasAll = obras.reduce((s, o) => s + (o.lancadas || []).length, 0);
    const valorLancadasAll = obras.reduce((s, o) => s + (o.lancadas || []).reduce((sv, n) => sv + n.valor, 0), 0);

    // Rankings — sempre todas as obras (visão comparativa)
    const rankingQtde = obras
      .map(o => ({ key: o.key, nome: o.nome || o.key, qtde: o.pendentes.length, valor: o.pendentes.reduce((sv, n) => sv + n.valor, 0) }))
      .filter(o => o.qtde > 0)
      .sort((a, b) => b.qtde - a.qtde);

    const rankingValor = obras
      .map(o => ({ key: o.key, nome: o.nome || o.key, qtde: o.pendentes.length, valor: o.pendentes.reduce((sv, n) => sv + n.valor, 0) }))
      .filter(o => o.valor > 0)
      .sort((a, b) => b.valor - a.valor);

    // Dados para gráfico — agrupados por mês
    const porMes: Record<string, { qtde: number; valor: number }> = {};
    notasResumo.forEach(n => {
      const mes = (n.data_emissao || '').slice(0, 7);
      if (!mes) return;
      if (!porMes[mes]) porMes[mes] = { qtde: 0, valor: 0 };
      porMes[mes].qtde++;
      porMes[mes].valor += n.valor;
    });
    const mesesOrd  = Object.keys(porMes).sort();
    const dadosQtde = mesesOrd.map(m => ({ label: this._formatarMes(m), valor: porMes[m].qtde }));
    const dadosValor = mesesOrd.map(m => ({ label: this._formatarMes(m), valor: porMes[m].valor }));

    // ── Dados para abas de lista ───────────────────────────────────────────────
    const opcoesObra = obras.map(o => ({ key: o.key, nome: o.nome || o.key }));
    const termo = filtro.toLowerCase();

    const notasPendentes = obras
      .filter(o => !filtroObra || o.key === filtroObra)
      .flatMap(o => o.pendentes.map(n => ({ ...n, obra_key: o.key, obra_nome: o.nome || o.key })))
      .filter(n => {
        if (!termo) return true;
        const tipoLabel = n.tipo === 'nfe' ? 'material' : 'servico';
        return (
          this._formatarData(n.data_emissao).includes(termo) ||
          (n.numero || '').toLowerCase().includes(termo) ||
          (n.nome_prest || '').toLowerCase().includes(termo) ||
          this._formatarCNPJ(n.cnpj_prest).includes(termo) ||
          this._formatarValor(n.valor).includes(termo) ||
          tipoLabel.includes(termo) ||
          n.obra_nome.toLowerCase().includes(termo)
        );
      })
      .sort((a, b) => {
        const cmp = sortField === 'valor'
          ? a.valor - b.valor
          : (a.data_emissao || '').localeCompare(b.data_emissao || '');
        return sortDir === 'asc' ? cmp : -cmp;
      });

    const notasLancadas = obras
      .filter(o => !filtroObra || o.key === filtroObra)
      .flatMap(o => (o.lancadas || []).map(n => ({ ...n, obra_key: o.key, obra_nome: o.nome || o.key })))
      .filter(n => {
        if (!termo) return true;
        const tipoLabel = n.tipo === 'nfe' ? 'material' : 'servico';
        return (
          this._formatarData(n.data_emissao).includes(termo) ||
          (n.numero || '').toLowerCase().includes(termo) ||
          (n.nome_prest || '').toLowerCase().includes(termo) ||
          this._formatarCNPJ(n.cnpj_prest).includes(termo) ||
          this._formatarValor(n.valor).includes(termo) ||
          tipoLabel.includes(termo) ||
          n.obra_nome.toLowerCase().includes(termo)
        );
      })
      .sort((a, b) => {
        const cmp = sortField === 'valor'
          ? a.valor - b.valor
          : (a.data_emissao || '').localeCompare(b.data_emissao || '');
        return sortDir === 'asc' ? cmp : -cmp;
      });

    const setaData  = sortField === 'data_emissao' ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';
    const setaValor = sortField === 'valor'        ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';

    return (
      <div className={styles.container}>

        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <span className={styles.titulo}>Monitor NFS-e</span>
            <span className={styles.subtitulo}>
              {abaAtiva === 'pendentes'
                ? 'Notas recebidas no SEFAZ nao lancadas no Sienge'
                : abaAtiva === 'lancadas'
                ? 'Notas ja lancadas no Sienge'
                : 'Visao geral — totais e rankings por obra'}
            </span>
          </div>
          <div className={styles.headerRight}>
            {!carregando && (
              <span className={totalPendentes > 0 ? styles.badgePendente : styles.badgeOk}>
                {totalPendentes > 0 ? `${totalPendentes} pendente(s)` : 'Tudo lancado'}
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
              onClick={() => this.setState({ abaAtiva: 'pendentes', filtro: '', filtroObra: '' })}
            >
              Pendentes ({totalPendentes})
            </button>
            <button
              className={abaAtiva === 'lancadas' ? styles.abaAtiva : styles.abaInativa}
              onClick={() => this.setState({ abaAtiva: 'lancadas', filtro: '', filtroObra: '' })}
            >
              Lancadas ({totalLancadas})
            </button>
            <button
              className={abaAtiva === 'resumo' ? styles.abaAtiva : styles.abaInativa}
              onClick={() => this.setState({ abaAtiva: 'resumo', filtro: '', filtroObra: '' })}
            >
              Resumo
            </button>
          </div>
        )}

        {/* Filtros — apenas nas abas de lista */}
        {!carregando && !erro && obras.length > 0 && abaAtiva !== 'resumo' && (
          <div className={styles.filtroBar}>
            <select
              value={filtroObra}
              onChange={e => this.setState({ filtroObra: e.target.value })}
              className={styles.filtroSelect}
            >
              <option value="">Todas as obras</option>
              {opcoesObra.map(o => (
                <option key={o.key} value={o.key}>{o.nome}</option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Filtrar por data, numero, prestador, CNPJ, valor ou tipo..."
              value={filtro}
              onChange={e => this.setState({ filtro: e.target.value })}
              className={styles.filtroInput}
            />
            {(filtro || filtroObra) && (
              <button className={styles.filtroClear} onClick={() => this.setState({ filtro: '', filtroObra: '' })}>
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

        {/* Tabela unificada — Pendentes */}
        {!carregando && !erro && abaAtiva === 'pendentes' && (
          notasPendentes.length === 0
            ? <div className={styles.vazio}>Nenhuma nota pendente de lancamento.</div>
            : (
              <div className={styles.obraCard}>
                <table className={styles.tabela}>
                  <thead>
                    <tr>
                      <th style={{width: '95px'}} className={styles.thSortable} onClick={() => this._toggleSort('data_emissao')} title="Clique para ordenar por data">
                        Data Emissao{setaData}
                      </th>
                      <th style={{width: '80px'}}>Nr</th>
                      <th style={{width: '120px'}}>Obra</th>
                      <th>Prestador</th>
                      <th style={{width: '148px'}}>CNPJ</th>
                      <th style={{width: '72px'}}>Tipo</th>
                      <th style={{width: '110px'}} className={`${styles.direita} ${styles.thSortable}`} onClick={() => this._toggleSort('valor')} title="Clique para ordenar por valor">
                        Valor (R$){setaValor}
                      </th>
                      <th style={{width: '60px'}}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {notasPendentes.map((nota, i) => (
                      <tr key={nota.chave || i}>
                        <td>{this._formatarData(nota.data_emissao)}</td>
                        <td className={styles.mono}>{nota.numero || '—'}</td>
                        <td>{nota.obra_nome}</td>
                        <td title={nota.nome_prest || ''}>{nota.nome_prest || '—'}</td>
                        <td className={styles.mono}>{this._formatarCNPJ(nota.cnpj_prest)}</td>
                        <td>{nota.tipo === 'nfe' ? 'Material' : 'Servico'}</td>
                        <td className={styles.direita}>{this._formatarValor(nota.valor)}</td>
                        <td className={styles.tdPdf}>
                          {nota.has_pdf && (
                            <a href={`${this.props.workerUrl.replace(/\/$/, '')}/api/pdf/${nota.chave}?token=${encodeURIComponent(this.props.apiToken)}`}
                              target="_blank" rel="noreferrer" className={styles.btnPdf} title="Ver DANFSe">
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
                        {this._formatarValor(notasPendentes.reduce((s, n) => s + n.valor, 0))}
                      </td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>
            )
        )}

        {/* Tabela unificada — Lancadas */}
        {!carregando && !erro && abaAtiva === 'lancadas' && (
          notasLancadas.length === 0
            ? <div className={styles.vazio}>Nenhuma nota lancada registrada ainda.</div>
            : (
              <div className={styles.obraCard}>
                <table className={`${styles.tabela} ${styles.tabelaLancada}`}>
                  <thead>
                    <tr>
                      <th style={{width: '95px'}} className={styles.thSortable} onClick={() => this._toggleSort('data_emissao')} title="Clique para ordenar por data">
                        Data Emissao{setaData}
                      </th>
                      <th style={{width: '80px'}}>Nr</th>
                      <th style={{width: '100px'}}>Titulo Sienge</th>
                      <th style={{width: '115px'}}>Obra</th>
                      <th>Prestador</th>
                      <th style={{width: '148px'}}>CNPJ</th>
                      <th style={{width: '72px'}}>Tipo</th>
                      <th style={{width: '110px'}} className={`${styles.direita} ${styles.thSortable}`} onClick={() => this._toggleSort('valor')} title="Clique para ordenar por valor">
                        Valor (R$){setaValor}
                      </th>
                      <th style={{width: '60px'}}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {notasLancadas.map((nota, i) => (
                      <tr key={nota.chave || i}>
                        <td>{this._formatarData(nota.data_emissao)}</td>
                        <td className={styles.mono}>{nota.numero || '—'}</td>
                        <td className={styles.mono}>{nota.numero_titulo || '—'}</td>
                        <td>{nota.obra_nome}</td>
                        <td title={nota.nome_prest || ''}>{nota.nome_prest || '—'}</td>
                        <td className={styles.mono}>{this._formatarCNPJ(nota.cnpj_prest)}</td>
                        <td>{nota.tipo === 'nfe' ? 'Material' : 'Servico'}</td>
                        <td className={styles.direita}>{this._formatarValor(nota.valor)}</td>
                        <td className={styles.tdPdf}>
                          {nota.has_pdf && (
                            <a href={`${this.props.workerUrl.replace(/\/$/, '')}/api/pdf/${nota.chave}?token=${encodeURIComponent(this.props.apiToken)}`}
                              target="_blank" rel="noreferrer" className={styles.btnPdf} title="Ver DANFSe">
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
                        {this._formatarValor(notasLancadas.reduce((s, n) => s + n.valor, 0))}
                      </td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>
            )
        )}

        {/* ── Aba Resumo ── */}
        {!carregando && !erro && abaAtiva === 'resumo' && (
          <div className={styles.resumo}>

            {/* Filtros do Resumo */}
            <div className={styles.resumoFiltroBar}>
              <select
                value={filtroResumoObra}
                onChange={e => this.setState({ filtroResumoObra: e.target.value })}
                className={styles.filtroSelect}
              >
                <option value="">Todas as obras</option>
                {opcoesObra.map(o => (
                  <option key={o.key} value={o.key}>{o.nome}</option>
                ))}
              </select>
              <div className={styles.mesesPills}>
                {mesesDisponiveis.map(m => {
                  const ativo = filtroResumoMeses.indexOf(m) >= 0;
                  return (
                    <button
                      key={m}
                      className={ativo ? styles.mesPillAtivo : styles.mesPill}
                      onClick={() => {
                        const novo = ativo
                          ? filtroResumoMeses.filter(x => x !== m)
                          : filtroResumoMeses.concat([m]);
                        this.setState({ filtroResumoMeses: novo });
                      }}
                    >
                      {this._formatarMes(m)}
                    </button>
                  );
                })}
              </div>
              {(filtroResumoObra || filtroResumoMeses.length > 0) && (
                <button className={styles.filtroClear} onClick={() => this.setState({ filtroResumoObra: '', filtroResumoMeses: [] })}>
                  X
                </button>
              )}
            </div>

            {/* Cards de totais */}
            <div className={styles.resumoCards}>
              <div className={`${styles.resumoCard} ${styles.resumoCardPendente}`}>
                <div className={styles.resumoCardLabel}>Pendentes</div>
                <div className={styles.resumoCardNumero}>{totalResumoQtde}</div>
                <div className={styles.resumoCardSub}>notas aguardando lancamento</div>
              </div>
              <div className={`${styles.resumoCard} ${styles.resumoCardValorPendente}`}>
                <div className={styles.resumoCardLabel}>Valor Total Pendente</div>
                <div className={styles.resumoCardNumero}>R$ {this._formatarValor(totalResumoValor)}</div>
                <div className={styles.resumoCardSub}>a lancar no Sienge</div>
              </div>
              <div className={`${styles.resumoCard} ${styles.resumoCardLancada}`}>
                <div className={styles.resumoCardLabel}>Lancadas 2026</div>
                <div className={styles.resumoCardNumero}>{totalLancadasAll}</div>
                <div className={styles.resumoCardSub}>R$ {this._formatarValor(valorLancadasAll)}</div>
              </div>
            </div>

            {/* Gráficos */}
            <div className={styles.chartRow}>
              <div className={styles.chartCard}>
                <div className={styles.chartTitle}>Qtde de Notas Pendentes por Mes de Emissao</div>
                {this._renderBarChart(dadosQtde, '#7B2C2C', v => this._numCompacto(v))}
              </div>
              <div className={styles.chartCard}>
                <div className={styles.chartTitle}>Valor Pendente por Mes de Emissao (R$)</div>
                {this._renderBarChart(dadosValor, '#1F4E79', v => this._numCompacto(v))}
              </div>
            </div>

            {/* Rankings — sempre todas as obras */}
            <div className={styles.resumoRankings}>
              <div className={styles.rankingCard}>
                <div className={styles.rankingTitle}>Pendentes por Obra (todas)</div>
                {rankingQtde.length === 0
                  ? <div className={styles.rankingVazio}>Nenhuma obra com pendentes.</div>
                  : rankingQtde.map((item, i) => (
                    <div key={item.key} className={styles.rankingItem}>
                      <span className={styles.rankingPos}>#{i + 1}</span>
                      <span className={styles.rankingNome} title={item.nome}>{item.nome}</span>
                      <span className={styles.rankingBadge}>{item.qtde} nota{item.qtde !== 1 ? 's' : ''}</span>
                    </div>
                  ))
                }
              </div>
              <div className={styles.rankingCard}>
                <div className={styles.rankingTitle}>Maior Valor Pendente por Obra (todas)</div>
                {rankingValor.length === 0
                  ? <div className={styles.rankingVazio}>Nenhuma obra com pendentes.</div>
                  : rankingValor.map((item, i) => (
                    <div key={item.key} className={styles.rankingItem}>
                      <span className={styles.rankingPos}>#{i + 1}</span>
                      <span className={styles.rankingNome} title={item.nome}>{item.nome}</span>
                      <span className={styles.rankingValorText}>R$ {this._formatarValor(item.valor)}</span>
                    </div>
                  ))
                }
              </div>
            </div>
          </div>
        )}

        {ultimaAtt && (
          <div className={styles.rodape}>
            Atualizado em: {ultimaAtt} &nbsp;|&nbsp; Fonte: SEFAZ ADN Nacional
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

  private _formatarMes(m: string): string {
    if (!m) return '';
    const [ano, mes] = m.split('-');
    const nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
    return `${nomes[parseInt(mes, 10) - 1]}/${ano.slice(2)}`;
  }
}
