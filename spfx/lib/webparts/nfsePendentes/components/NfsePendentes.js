var __extends = (this && this.__extends) || (function () {
    var extendStatics = function (d, b) {
        extendStatics = Object.setPrototypeOf ||
            ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
            function (d, b) { for (var p in b) if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p]; };
        return extendStatics(d, b);
    };
    return function (d, b) {
        if (typeof b !== "function" && b !== null)
            throw new TypeError("Class extends value " + String(b) + " is not a constructor or null");
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };
})();
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (_) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
import * as React from 'react';
import styles from './NfsePendentes.module.scss';
var NfsePendentes = /** @class */ (function (_super) {
    __extends(NfsePendentes, _super);
    function NfsePendentes(props) {
        var _this = _super.call(this, props) || this;
        _this.state = {
            obras: [], carregando: true, erro: '', ultimaAtt: '', filtro: '',
            sortField: 'data_emissao', sortDir: 'desc', abaAtiva: 'pendentes',
            filtroResumoMeses: [],
            filtroAno: '',
            filtroMes: '',
        };
        return _this;
    }
    NfsePendentes.prototype.componentDidMount = function () {
        this._carregarDados().catch(console.error);
    };
    NfsePendentes.prototype.componentDidUpdate = function (prevProps) {
        if (prevProps.workerUrl !== this.props.workerUrl ||
            prevProps.apiToken !== this.props.apiToken ||
            prevProps.exibirLancadas !== this.props.exibirLancadas) {
            this._carregarDados().catch(console.error);
        }
    };
    NfsePendentes.prototype._carregarDados = function () {
        return __awaiter(this, void 0, void 0, function () {
            var _a, workerUrl, apiToken, url, resp, txt, dados, obrasNormalizadas, obras, e_1;
            var _this = this;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        this.setState({ carregando: true, erro: '' });
                        _a = this.props, workerUrl = _a.workerUrl, apiToken = _a.apiToken;
                        if (!workerUrl || !apiToken) {
                            this.setState({ carregando: false, erro: 'Configure a URL do Worker e o Token nas propriedades do web part.' });
                            return [2 /*return*/];
                        }
                        url = "".concat(workerUrl.replace(/\/$/, ''), "/api/pendentes?token=").concat(encodeURIComponent(apiToken));
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 6, , 7]);
                        return [4 /*yield*/, fetch(url)];
                    case 2:
                        resp = _b.sent();
                        if (!!resp.ok) return [3 /*break*/, 4];
                        return [4 /*yield*/, resp.text()];
                    case 3:
                        txt = _b.sent();
                        throw new Error("Erro ".concat(resp.status, ": ").concat(txt.substring(0, 200)));
                    case 4: return [4 /*yield*/, resp.json()];
                    case 5:
                        dados = _b.sent();
                        obrasNormalizadas = dados.map(function (o) { return (__assign(__assign({}, o), { pendentes: (o.pendentes || []).map(function (n) { return (__assign(__assign({}, n), { valor: _this._toFloat(n.valor) })); }), lancadas: (o.lancadas || []).map(function (n) { return (__assign(__assign({}, n), { valor: _this._toFloat(n.valor) })); }) })); });
                        obras = obrasNormalizadas
                            .sort(function (a, b) { return a.key.localeCompare(b.key); });
                        this.setState({ obras: obras, carregando: false, ultimaAtt: new Date().toLocaleString('pt-BR') });
                        return [3 /*break*/, 7];
                    case 6:
                        e_1 = _b.sent();
                        this.setState({ carregando: false, erro: e_1.message || String(e_1) });
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    };
    NfsePendentes.prototype._toFloat = function (v) {
        if (typeof v === 'number')
            return v;
        var s = String(v || '0');
        if (s.includes(',')) {
            return parseFloat(s.replace(/\./g, '').replace(',', '.')) || 0;
        }
        return parseFloat(s) || 0;
    };
    NfsePendentes.prototype._toggleSort = function (field) {
        this.setState(function (s) { return ({
            sortField: field,
            sortDir: s.sortField === field && s.sortDir === 'asc' ? 'desc' : 'asc',
        }); });
    };
    // ── Gráfico SVG ────────────────────────────────────────────────────────────
    NfsePendentes.prototype._numCompacto = function (v) {
        if (v === 0)
            return '0';
        if (v >= 1000000)
            return "".concat((v / 1000000).toFixed(1), "M");
        if (v >= 1000)
            return "".concat((v / 1000).toFixed(0), "k");
        return v.toFixed(0);
    };
    NfsePendentes.prototype._renderBarChart = function (dados, cor, fmtY) {
        if (dados.length === 0) {
            return React.createElement("div", { className: styles.chartVazio }, "Sem dados para o periodo selecionado.");
        }
        var VW = 360, VH = 165;
        var pl = 44, pr = 8, pt = 14, pb = 34;
        var cw = VW - pl - pr;
        var ch = VH - pt - pb;
        var maxVal = Math.max.apply(Math, __spreadArray(__spreadArray([], dados.map(function (d) { return d.valor; }), false), [1], false));
        var n = dados.length;
        var slot = cw / n;
        var barW = Math.min(slot * 0.62, 38);
        var nTicks = 4;
        var rotacionar = n > 5;
        return (React.createElement("svg", { viewBox: "0 0 ".concat(VW, " ").concat(VH), style: { width: '100%', height: 'auto' } },
            Array.from({ length: nTicks + 1 }, function (_, i) {
                var ratio = i / nTicks;
                var y = pt + ch * (1 - ratio);
                return (React.createElement("g", { key: i },
                    React.createElement("line", { x1: pl, y1: y, x2: pl + cw, y2: y, stroke: "#f0f0f0", strokeWidth: "1" }),
                    React.createElement("text", { x: pl - 3, y: y + 3, fontSize: "8", textAnchor: "end", fill: "#b0b0b0" }, fmtY(maxVal * ratio))));
            }),
            React.createElement("line", { x1: pl, y1: pt, x2: pl, y2: pt + ch, stroke: "#ddd", strokeWidth: "1" }),
            React.createElement("line", { x1: pl, y1: pt + ch, x2: pl + cw, y2: pt + ch, stroke: "#ddd", strokeWidth: "1" }),
            dados.map(function (d, i) {
                var barH = Math.max((d.valor / maxVal) * ch, d.valor > 0 ? 2 : 0);
                var x = pl + i * slot + (slot - barW) / 2;
                var y = pt + ch - barH;
                var cx2 = x + barW / 2;
                var ly = pt + ch + 16;
                return (React.createElement("g", { key: i },
                    React.createElement("rect", { x: x, y: y, width: barW, height: barH, fill: cor, rx: "2", opacity: "0.85" }),
                    d.valor > 0 && barH > 12 && (React.createElement("text", { x: cx2, y: y - 2, fontSize: "7", textAnchor: "middle", fill: cor, fontWeight: "600" }, fmtY(d.valor))),
                    React.createElement("text", { x: cx2, y: ly, fontSize: "8", textAnchor: rotacionar ? 'end' : 'middle', fill: "#888", transform: rotacionar ? "rotate(-38, ".concat(cx2, ", ").concat(ly, ")") : undefined }, d.label)));
            })));
    };
    // ── Render principal ────────────────────────────────────────────────────────
    NfsePendentes.prototype.render = function () {
        var _this = this;
        var _a = this.state, carregando = _a.carregando, erro = _a.erro, obras = _a.obras, ultimaAtt = _a.ultimaAtt, filtro = _a.filtro, sortField = _a.sortField, sortDir = _a.sortDir, abaAtiva = _a.abaAtiva, filtroResumoMeses = _a.filtroResumoMeses, filtroAno = _a.filtroAno, filtroMes = _a.filtroMes;
        var totalPendentes = obras.reduce(function (s, o) { return s + o.pendentes.length; }, 0);
        var totalLancadas = obras.reduce(function (s, o) { return s + (o.lancadas || []).length; }, 0);
        // ── Dados para aba Resumo ─────────────────────────────────────────────────
        // Meses disponíveis (ordenados decrescente para o dropdown)
        var mesesSet = {};
        obras.forEach(function (o) { return o.pendentes.forEach(function (n) {
            if (n.tipo === 'nfse') {
                var m = (n.data_emissao || '').slice(0, 7);
                if (m.length === 7)
                    mesesSet[m] = true;
            }
        }); });
        var mesesDisponiveis = Object.keys(mesesSet).sort().reverse();
        // Extrair anos únicos dos meses disponíveis
        var anosSet = new Set(mesesDisponiveis.map(function (m) { return m.slice(0, 4); }));
        var anosDisponiveis = Array.from(anosSet).sort().reverse();
        // Filtrar meses baseado no ano selecionado
        var mesesFiltrados = filtroAno
            ? mesesDisponiveis.filter(function (m) { return m.startsWith(filtroAno); })
            : mesesDisponiveis;
        // Se ano + mês selecionados, aplicar filtro
        if (filtroAno && filtroMes) {
            this.setState(function (s) {
                var mesSelecionado = "".concat(filtroAno, "-").concat(filtroMes);
                if (s.filtroResumoMeses.indexOf(mesSelecionado) < 0) {
                    return { filtroResumoMeses: [mesSelecionado] };
                }
                return null;
            });
        }
        var obrasResumo = obras;
        var notasResumo = obrasResumo
            .flatMap(function (o) { return o.pendentes; })
            .filter(function (n) { return n.tipo === 'nfse'; })
            .filter(function (n) { return filtroResumoMeses.length === 0 || filtroResumoMeses.indexOf((n.data_emissao || '').slice(0, 7)) >= 0; });
        var totalResumoQtde = notasResumo.length;
        var totalResumoValor = notasResumo.reduce(function (s, n) { return s + n.valor; }, 0);
        var totalLancadasAll = obras.reduce(function (s, o) { return s + (o.lancadas || []).filter(function (n) { return n.tipo === 'nfse'; }).length; }, 0);
        var valorLancadasAll = obras.reduce(function (s, o) { return s + (o.lancadas || []).filter(function (n) { return n.tipo === 'nfse'; }).reduce(function (sv, n) { return sv + n.valor; }, 0); }, 0);
        // Rankings — sempre todas as obras (visão comparativa)
        var rankingQtde = obras
            .map(function (o) {
            var notas = o.pendentes.filter(function (n) { return n.tipo === 'nfse'; });
            return { key: o.key, nome: o.nome || o.key, qtde: notas.length, valor: notas.reduce(function (sv, n) { return sv + n.valor; }, 0) };
        })
            .filter(function (o) { return o.qtde > 0; })
            .sort(function (a, b) { return b.qtde - a.qtde; });
        var rankingValor = obras
            .map(function (o) {
            var notas = o.pendentes.filter(function (n) { return n.tipo === 'nfse'; });
            return { key: o.key, nome: o.nome || o.key, qtde: notas.length, valor: notas.reduce(function (sv, n) { return sv + n.valor; }, 0) };
        })
            .filter(function (o) { return o.valor > 0; })
            .sort(function (a, b) { return b.valor - a.valor; });
        // Dados para gráfico — agrupados por mês
        var porMes = {};
        notasResumo.forEach(function (n) {
            var mes = (n.data_emissao || '').slice(0, 7);
            if (!mes)
                return;
            if (!porMes[mes])
                porMes[mes] = { qtde: 0, valor: 0 };
            porMes[mes].qtde++;
            porMes[mes].valor += n.valor;
        });
        var mesesOrd = Object.keys(porMes).sort();
        var dadosQtde = mesesOrd.map(function (m) { return ({ label: _this._formatarMes(m), valor: porMes[m].qtde }); });
        var dadosValor = mesesOrd.map(function (m) { return ({ label: _this._formatarMes(m), valor: porMes[m].valor }); });
        // ── Dados para abas de lista ───────────────────────────────────────────────
        var termo = filtro.toLowerCase();
        var notasPendentes = obras
            .flatMap(function (o) { return o.pendentes.map(function (n) { return (__assign(__assign({}, n), { obra_key: o.key, obra_nome: o.nome || o.key })); }); })
            .filter(function (n) { return n.tipo === 'nfse'; })
            .filter(function (n) {
            if (!termo)
                return true;
            var tipoLabel = n.tipo === 'nfe' ? 'material' : 'servico';
            return (_this._formatarData(n.data_emissao).includes(termo) ||
                (n.numero || '').toLowerCase().includes(termo) ||
                (n.nome_prest || '').toLowerCase().includes(termo) ||
                _this._formatarCNPJ(n.cnpj_prest).includes(termo) ||
                _this._formatarValor(n.valor).includes(termo) ||
                tipoLabel.includes(termo) ||
                n.obra_nome.toLowerCase().includes(termo));
        })
            .sort(function (a, b) {
            var cmp = sortField === 'valor'
                ? a.valor - b.valor
                : (a.data_emissao || '').localeCompare(b.data_emissao || '');
            return sortDir === 'asc' ? cmp : -cmp;
        });
        var notasLancadas = obras
            .flatMap(function (o) { return (o.lancadas || []).map(function (n) { return (__assign(__assign({}, n), { obra_key: o.key, obra_nome: o.nome || o.key })); }); })
            .filter(function (n) { return n.tipo === 'nfse'; })
            .filter(function (n) {
            if (!termo)
                return true;
            var tipoLabel = n.tipo === 'nfe' ? 'material' : 'servico';
            return (_this._formatarData(n.data_emissao).includes(termo) ||
                (n.numero || '').toLowerCase().includes(termo) ||
                (n.nome_prest || '').toLowerCase().includes(termo) ||
                _this._formatarCNPJ(n.cnpj_prest).includes(termo) ||
                _this._formatarValor(n.valor).includes(termo) ||
                tipoLabel.includes(termo) ||
                n.obra_nome.toLowerCase().includes(termo));
        })
            .sort(function (a, b) {
            var cmp = sortField === 'valor'
                ? a.valor - b.valor
                : (a.data_emissao || '').localeCompare(b.data_emissao || '');
            return sortDir === 'asc' ? cmp : -cmp;
        });
        var setaData = sortField === 'data_emissao' ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';
        var setaValor = sortField === 'valor' ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';
        return (React.createElement("div", { className: styles.container },
            React.createElement("div", { className: styles.header },
                React.createElement("div", { className: styles.headerLeft },
                    React.createElement("span", { className: styles.titulo }, "Monitor NFS-e"),
                    React.createElement("span", { className: styles.subtitulo }, abaAtiva === 'pendentes'
                        ? 'Notas recebidas no SEFAZ nao lancadas no Sienge'
                        : abaAtiva === 'lancadas'
                            ? 'Notas ja lancadas no Sienge'
                            : 'Visao geral — totais e rankings por obra')),
                React.createElement("div", { className: styles.headerRight },
                    !carregando && (React.createElement("span", { className: totalPendentes > 0 ? styles.badgePendente : styles.badgeOk }, totalPendentes > 0 ? "".concat(totalPendentes, " pendente(s)") : 'Tudo lancado')),
                    React.createElement("button", { className: styles.btnAtualizar, onClick: function () { return _this._carregarDados(); } }, "Atualizar"))),
            !carregando && !erro && (React.createElement("div", { className: styles.abas },
                React.createElement("button", { className: abaAtiva === 'pendentes' ? styles.abaAtiva : styles.abaInativa, onClick: function () { return _this.setState({ abaAtiva: 'pendentes', filtro: '' }); } },
                    "Pendentes (",
                    totalPendentes,
                    ")"),
                React.createElement("button", { className: abaAtiva === 'lancadas' ? styles.abaAtiva : styles.abaInativa, onClick: function () { return _this.setState({ abaAtiva: 'lancadas', filtro: '' }); } },
                    "Lancadas (",
                    totalLancadas,
                    ")"),
                React.createElement("button", { className: abaAtiva === 'resumo' ? styles.abaAtiva : styles.abaInativa, onClick: function () { return _this.setState({ abaAtiva: 'resumo', filtro: '' }); } }, "Resumo"))),
            !carregando && !erro && obras.length > 0 && abaAtiva !== 'resumo' && (React.createElement("div", { className: styles.filtroBar },
                React.createElement("input", { type: "text", placeholder: "Filtrar por data, numero, prestador, CNPJ ou valor...", value: filtro, onChange: function (e) { return _this.setState({ filtro: e.target.value }); }, className: styles.filtroInput }),
                filtro && (React.createElement("button", { className: styles.filtroClear, onClick: function () { return _this.setState({ filtro: '' }); } }, "X")))),
            carregando && React.createElement("div", { className: styles.loading }, "Carregando dados..."),
            erro && (React.createElement("div", { className: styles.erro },
                React.createElement("strong", null, "Erro ao carregar dados:"),
                React.createElement("br", null),
                erro)),
            !carregando && !erro && abaAtiva === 'pendentes' && (notasPendentes.length === 0
                ? React.createElement("div", { className: styles.vazio }, "Nenhuma nota pendente de lancamento.")
                : (React.createElement("div", { className: styles.obraCard },
                    React.createElement("table", { className: styles.tabela },
                        React.createElement("thead", null,
                            React.createElement("tr", null,
                                React.createElement("th", { style: { width: '95px' }, className: styles.thSortable, onClick: function () { return _this._toggleSort('data_emissao'); }, title: "Clique para ordenar por data" },
                                    "Data Emissao",
                                    setaData),
                                React.createElement("th", { style: { width: '80px' } }, "Nr"),
                                React.createElement("th", { style: { width: '140px' } }, "Chave"),
                                React.createElement("th", { style: { width: '120px' } }, "Obra"),
                                React.createElement("th", null, "Prestador"),
                                React.createElement("th", { style: { width: '148px' } }, "CNPJ"),
                                React.createElement("th", { style: { width: '72px' } }, "Tipo"),
                                React.createElement("th", { style: { width: '110px' }, className: "".concat(styles.direita, " ").concat(styles.thSortable), onClick: function () { return _this._toggleSort('valor'); }, title: "Clique para ordenar por valor" },
                                    "Valor (R$)",
                                    setaValor),
                                React.createElement("th", { style: { width: '60px' } }))),
                        React.createElement("tbody", null, notasPendentes.map(function (nota, i) { return (React.createElement("tr", { key: nota.chave || i },
                            React.createElement("td", null, _this._formatarData(nota.data_emissao)),
                            React.createElement("td", { className: styles.mono }, nota.numero || '—'),
                            React.createElement("td", { className: styles.mono, title: "Clique para copiar", style: { cursor: 'pointer', color: '#0078d4' }, onClick: function () { navigator.clipboard.writeText(nota.chave || ''); alert('Chave copiada!'); } }, nota.chave ? nota.chave.substring(0, 12) + '...' : '—'),
                            React.createElement("td", null, nota.obra_nome),
                            React.createElement("td", { title: nota.nome_prest || '' }, nota.nome_prest || '—'),
                            React.createElement("td", { className: styles.mono }, _this._formatarCNPJ(nota.cnpj_prest)),
                            React.createElement("td", null, nota.tipo === 'nfe' ? 'Material' : 'Servico'),
                            React.createElement("td", { className: styles.direita }, _this._formatarValor(nota.valor)),
                            React.createElement("td", { className: styles.tdPdf }, nota.has_pdf ? (React.createElement("a", { href: "".concat(_this.props.workerUrl.replace(/\/$/, ''), "/api/pdf/").concat(nota.chave, "?token=").concat(encodeURIComponent(_this.props.apiToken)), target: "_blank", rel: "noreferrer", className: styles.btnPdf, title: "Ver DANFSe" }, "PDF")) : (React.createElement("span", { className: styles.pdfIndisponivel, title: "PDF ainda n\u00E3o disponibilizado pela SEFAZ" }, "\u2014"))))); })),
                        React.createElement("tfoot", null,
                            React.createElement("tr", null,
                                React.createElement("td", { colSpan: 7, className: styles.totalLabel }, "TOTAL PENDENTE"),
                                React.createElement("td", { className: "".concat(styles.direita, " ").concat(styles.totalValor) }, this._formatarValor(notasPendentes.reduce(function (s, n) { return s + n.valor; }, 0))),
                                React.createElement("td", null))))))),
            !carregando && !erro && abaAtiva === 'lancadas' && (notasLancadas.length === 0
                ? React.createElement("div", { className: styles.vazio }, "Nenhuma nota lancada registrada ainda.")
                : (React.createElement("div", { className: styles.obraCard },
                    React.createElement("table", { className: "".concat(styles.tabela, " ").concat(styles.tabelaLancada) },
                        React.createElement("thead", null,
                            React.createElement("tr", null,
                                React.createElement("th", { style: { width: '95px' }, className: styles.thSortable, onClick: function () { return _this._toggleSort('data_emissao'); }, title: "Clique para ordenar por data" },
                                    "Data Emissao",
                                    setaData),
                                React.createElement("th", { style: { width: '80px' } }, "Nr"),
                                React.createElement("th", { style: { width: '140px' } }, "Chave"),
                                React.createElement("th", { style: { width: '100px' } }, "Titulo Sienge"),
                                React.createElement("th", { style: { width: '115px' } }, "Obra"),
                                React.createElement("th", null, "Prestador"),
                                React.createElement("th", { style: { width: '148px' } }, "CNPJ"),
                                React.createElement("th", { style: { width: '72px' } }, "Tipo"),
                                React.createElement("th", { style: { width: '110px' }, className: "".concat(styles.direita, " ").concat(styles.thSortable), onClick: function () { return _this._toggleSort('valor'); }, title: "Clique para ordenar por valor" },
                                    "Valor (R$)",
                                    setaValor),
                                React.createElement("th", { style: { width: '60px' } }))),
                        React.createElement("tbody", null, notasLancadas.map(function (nota, i) { return (React.createElement("tr", { key: nota.chave || i },
                            React.createElement("td", null, _this._formatarData(nota.data_emissao)),
                            React.createElement("td", { className: styles.mono }, nota.numero || '—'),
                            React.createElement("td", { className: styles.mono, title: "Clique para copiar", style: { cursor: 'pointer', color: '#0078d4' }, onClick: function () { navigator.clipboard.writeText(nota.chave || ''); alert('Chave copiada!'); } }, nota.chave ? nota.chave.substring(0, 12) + '...' : '—'),
                            React.createElement("td", { className: styles.mono }, nota.numero_titulo || '—'),
                            React.createElement("td", null, nota.obra_nome),
                            React.createElement("td", { title: nota.nome_prest || '' }, nota.nome_prest || '—'),
                            React.createElement("td", { className: styles.mono }, _this._formatarCNPJ(nota.cnpj_prest)),
                            React.createElement("td", null, nota.tipo === 'nfe' ? 'Material' : 'Servico'),
                            React.createElement("td", { className: styles.direita }, _this._formatarValor(nota.valor)),
                            React.createElement("td", { className: styles.tdPdf }, nota.has_pdf ? (React.createElement("a", { href: "".concat(_this.props.workerUrl.replace(/\/$/, ''), "/api/pdf/").concat(nota.chave, "?token=").concat(encodeURIComponent(_this.props.apiToken)), target: "_blank", rel: "noreferrer", className: styles.btnPdf, title: "Ver DANFSe" }, "PDF")) : (React.createElement("span", { className: styles.pdfIndisponivel, title: "PDF ainda n\u00E3o disponibilizado pela SEFAZ" }, "\u2014"))))); })),
                        React.createElement("tfoot", null,
                            React.createElement("tr", null,
                                React.createElement("td", { colSpan: 8, className: styles.totalLabel }, "TOTAL LANCADO"),
                                React.createElement("td", { className: "".concat(styles.direita, " ").concat(styles.totalValorLancada) }, this._formatarValor(notasLancadas.reduce(function (s, n) { return s + n.valor; }, 0))),
                                React.createElement("td", null))))))),
            !carregando && !erro && abaAtiva === 'resumo' && (React.createElement("div", { className: styles.resumo },
                React.createElement("div", { className: styles.resumoFiltroBar },
                    React.createElement("div", { className: styles.filtroSelectGroup },
                        React.createElement("label", null, "Ano:"),
                        React.createElement("select", { value: filtroAno, onChange: function (e) {
                                _this.setState({ filtroAno: e.target.value, filtroMes: '' });
                            } },
                            React.createElement("option", { value: "" }, "Todos"),
                            anosDisponiveis.map(function (ano) { return (React.createElement("option", { key: ano, value: ano }, ano)); })),
                        React.createElement("label", null, "M\u00EAs:"),
                        React.createElement("select", { value: filtroMes, onChange: function (e) {
                                _this.setState({ filtroMes: e.target.value });
                            }, disabled: !filtroAno },
                            React.createElement("option", { value: "" }, "Todos"),
                            mesesFiltrados.map(function (m) {
                                var mes = m.slice(5, 7);
                                return (React.createElement("option", { key: m, value: mes },
                                    _this._formatarMes(m).split('/')[1],
                                    " - ",
                                    _this._formatarMes(m).split('/')[0]));
                            }))),
                    filtroResumoMeses.length > 0 && (React.createElement("button", { className: styles.filtroClear, onClick: function () { return _this.setState({ filtroResumoMeses: [], filtroAno: '', filtroMes: '' }); } }, "Limpar Filtro"))),
                React.createElement("div", { className: styles.resumoCards },
                    React.createElement("div", { className: "".concat(styles.resumoCard, " ").concat(styles.resumoCardPendente) },
                        React.createElement("div", { className: styles.resumoCardLabel }, "Pendentes"),
                        React.createElement("div", { className: styles.resumoCardNumero }, totalResumoQtde),
                        React.createElement("div", { className: styles.resumoCardSub }, "notas aguardando lancamento")),
                    React.createElement("div", { className: "".concat(styles.resumoCard, " ").concat(styles.resumoCardValorPendente) },
                        React.createElement("div", { className: styles.resumoCardLabel }, "Valor Total Pendente"),
                        React.createElement("div", { className: styles.resumoCardNumero },
                            "R$ ",
                            this._formatarValor(totalResumoValor)),
                        React.createElement("div", { className: styles.resumoCardSub }, "a lancar no Sienge")),
                    React.createElement("div", { className: "".concat(styles.resumoCard, " ").concat(styles.resumoCardLancada) },
                        React.createElement("div", { className: styles.resumoCardLabel }, "Lancadas 2026"),
                        React.createElement("div", { className: styles.resumoCardNumero }, totalLancadasAll),
                        React.createElement("div", { className: styles.resumoCardSub },
                            "R$ ",
                            this._formatarValor(valorLancadasAll)))),
                React.createElement("div", { className: styles.chartRow },
                    React.createElement("div", { className: styles.chartCard },
                        React.createElement("div", { className: styles.chartTitle }, "Qtde de Notas Pendentes por Mes de Emissao"),
                        this._renderBarChart(dadosQtde, '#7B2C2C', function (v) { return _this._numCompacto(v); })),
                    React.createElement("div", { className: styles.chartCard },
                        React.createElement("div", { className: styles.chartTitle }, "Valor Pendente por Mes de Emissao (R$)"),
                        this._renderBarChart(dadosValor, '#1F4E79', function (v) { return _this._numCompacto(v); }))),
                React.createElement("div", { className: styles.resumoRankings },
                    React.createElement("div", { className: styles.rankingCard },
                        React.createElement("div", { className: styles.rankingTitle }, "Pendentes por Obra (todas)"),
                        rankingQtde.length === 0
                            ? React.createElement("div", { className: styles.rankingVazio }, "Nenhuma obra com pendentes.")
                            : rankingQtde.map(function (item, i) { return (React.createElement("div", { key: item.key, className: styles.rankingItem },
                                React.createElement("span", { className: styles.rankingPos },
                                    "#",
                                    i + 1),
                                React.createElement("span", { className: styles.rankingNome, title: item.nome }, item.nome),
                                React.createElement("span", { className: styles.rankingBadge },
                                    item.qtde,
                                    " nota",
                                    item.qtde !== 1 ? 's' : ''))); })),
                    React.createElement("div", { className: styles.rankingCard },
                        React.createElement("div", { className: styles.rankingTitle }, "Maior Valor Pendente por Obra (todas)"),
                        rankingValor.length === 0
                            ? React.createElement("div", { className: styles.rankingVazio }, "Nenhuma obra com pendentes.")
                            : rankingValor.map(function (item, i) { return (React.createElement("div", { key: item.key, className: styles.rankingItem },
                                React.createElement("span", { className: styles.rankingPos },
                                    "#",
                                    i + 1),
                                React.createElement("span", { className: styles.rankingNome, title: item.nome }, item.nome),
                                React.createElement("span", { className: styles.rankingValorText },
                                    "R$ ",
                                    _this._formatarValor(item.valor)))); }))))),
            ultimaAtt && (React.createElement("div", { className: styles.rodape },
                "Atualizado em: ",
                ultimaAtt,
                " \u00A0|\u00A0 Fonte: SEFAZ ADN Nacional"))));
    };
    NfsePendentes.prototype._formatarData = function (s) {
        if (!s)
            return '—';
        var _a = s.split('-'), ano = _a[0], mes = _a[1], dia = _a[2];
        return dia && mes && ano ? "".concat(dia, "/").concat(mes, "/").concat(ano) : s;
    };
    NfsePendentes.prototype._formatarValor = function (v) {
        return (v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };
    NfsePendentes.prototype._formatarCNPJ = function (s) {
        var d = (s || '').replace(/\D/g, '');
        if (d.length !== 14)
            return s || '—';
        return "".concat(d.slice(0, 2), ".").concat(d.slice(2, 5), ".").concat(d.slice(5, 8), "/").concat(d.slice(8, 12), "-").concat(d.slice(12));
    };
    NfsePendentes.prototype._formatarMes = function (m) {
        if (!m)
            return '';
        var _a = m.split('-'), ano = _a[0], mes = _a[1];
        var nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
        return "".concat(nomes[parseInt(mes, 10) - 1], "/").concat(ano.slice(2));
    };
    return NfsePendentes;
}(React.Component));
export default NfsePendentes;
//# sourceMappingURL=NfsePendentes.js.map