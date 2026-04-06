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
import * as React from 'react';
import * as ReactDom from 'react-dom';
import { Version } from '@microsoft/sp-core-library';
import { PropertyPaneTextField, PropertyPaneToggle, } from '@microsoft/sp-property-pane';
import { BaseClientSideWebPart } from '@microsoft/sp-webpart-base';
import NfsePendentes from './components/NfsePendentes';
var NfsePendentesWebPart = /** @class */ (function (_super) {
    __extends(NfsePendentesWebPart, _super);
    function NfsePendentesWebPart() {
        return _super !== null && _super.apply(this, arguments) || this;
    }
    NfsePendentesWebPart.prototype.render = function () {
        var element = React.createElement(NfsePendentes, {
            workerUrl: this.properties.workerUrl || '',
            apiToken: this.properties.apiToken || '',
            exibirLancadas: this.properties.exibirLancadas,
            userDisplayName: this.context.pageContext.user.displayName,
        });
        ReactDom.render(element, this.domElement);
    };
    NfsePendentesWebPart.prototype.onDispose = function () {
        ReactDom.unmountComponentAtNode(this.domElement);
    };
    Object.defineProperty(NfsePendentesWebPart.prototype, "dataVersion", {
        get: function () {
            return Version.parse('1.0');
        },
        enumerable: false,
        configurable: true
    });
    NfsePendentesWebPart.prototype.getPropertyPaneConfiguration = function () {
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
    };
    return NfsePendentesWebPart;
}(BaseClientSideWebPart));
export default NfsePendentesWebPart;
//# sourceMappingURL=NfsePendentesWebPart.js.map