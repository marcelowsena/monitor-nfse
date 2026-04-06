import { Version } from '@microsoft/sp-core-library';
import { IPropertyPaneConfiguration } from '@microsoft/sp-property-pane';
import { BaseClientSideWebPart } from '@microsoft/sp-webpart-base';
export interface INfsePendentesWebPartProps {
    workerUrl: string;
    apiToken: string;
    exibirLancadas: boolean;
}
export default class NfsePendentesWebPart extends BaseClientSideWebPart<INfsePendentesWebPartProps> {
    render(): void;
    protected onDispose(): void;
    protected get dataVersion(): Version;
    protected getPropertyPaneConfiguration(): IPropertyPaneConfiguration;
}
//# sourceMappingURL=NfsePendentesWebPart.d.ts.map