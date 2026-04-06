import * as React from 'react';
import { INfsePendentesProps, IObra } from './INfsePendentesProps';
declare type SortDir = 'asc' | 'desc';
declare type SortField = 'data_emissao' | 'valor';
declare type Aba = 'pendentes' | 'lancadas' | 'resumo';
interface IState {
    obras: IObra[];
    carregando: boolean;
    erro: string;
    ultimaAtt: string;
    filtro: string;
    sortField: SortField;
    sortDir: SortDir;
    abaAtiva: Aba;
    filtroResumoMeses: string[];
}
export default class NfsePendentes extends React.Component<INfsePendentesProps, IState> {
    constructor(props: INfsePendentesProps);
    componentDidMount(): void;
    componentDidUpdate(prevProps: INfsePendentesProps): void;
    private _carregarDados;
    private _toFloat;
    private _toggleSort;
    private _numCompacto;
    private _renderBarChart;
    render(): React.ReactElement;
    private _formatarData;
    private _formatarValor;
    private _formatarCNPJ;
    private _formatarMes;
}
export {};
//# sourceMappingURL=NfsePendentes.d.ts.map