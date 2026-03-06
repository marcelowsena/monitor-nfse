import * as React from 'react';
import * as ReactDom from 'react-dom';
import { Version } from '@microsoft/sp-core-library';
import {
  IPropertyPaneConfiguration,
  PropertyPaneTextField,
  PropertyPaneToggle,
} from '@microsoft/sp-property-pane';
import { BaseClientSideWebPart } from '@microsoft/sp-webpart-base';

import NfsePendentes from './components/NfsePendentes';
import { INfsePendentesProps } from './components/INfsePendentesProps';

export interface INfsePendentesWebPartProps {
  workerUrl:      string;
  apiToken:       string;
  exibirLancadas: boolean;
}

export default class NfsePendentesWebPart extends BaseClientSideWebPart<INfsePendentesWebPartProps> {

  public render(): void {
    const element: React.ReactElement<INfsePendentesProps> = React.createElement(
      NfsePendentes,
      {
        workerUrl:       this.properties.workerUrl  || '',
        apiToken:        this.properties.apiToken   || '',
        exibirLancadas:  this.properties.exibirLancadas,
        userDisplayName: this.context.pageContext.user.displayName,
      }
    );
    ReactDom.render(element, this.domElement);
  }

  protected onDispose(): void {
    ReactDom.unmountComponentAtNode(this.domElement);
  }

  protected get dataVersion(): Version {
    return Version.parse('1.0');
  }

  protected getPropertyPaneConfiguration(): IPropertyPaneConfiguration {
    return {
      pages: [{
        header: { description: 'Configurações do Monitor NFS-e' },
        groups: [{
          groupName: 'Cloudflare Worker',
          groupFields: [
            PropertyPaneTextField('workerUrl', {
              label: 'URL do Worker (ex: https://monitor-nfse.empresa.workers.dev)',
              value: this.properties.workerUrl,
            }),
            PropertyPaneTextField('apiToken', {
              label: 'Token da API (CF_API_TOKEN)',
              value: this.properties.apiToken,
            }),
            PropertyPaneToggle('exibirLancadas', {
              label: 'Exibir notas já lançadas',
              onText: 'Sim',
              offText: 'Não',
            }),
          ],
        }],
      }],
    };
  }
}
