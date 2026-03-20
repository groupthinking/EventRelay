"use strict";
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
/* tslint:disable */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const App_1 = __importDefault(require("@/App"));
const context_1 = require("@/context");
const react_1 = __importDefault(require("react"));
const client_1 = __importDefault(require("react-dom/client"));
function DataProvider({ children }) {
    const [examples, setExamples] = react_1.default.useState([]);
    const [isLoading, setIsLoading] = react_1.default.useState(true);
    react_1.default.useEffect(() => {
        setIsLoading(true);
        fetch('data/examples.json')
            .then((res) => res.json())
            .then((fetchedData) => {
            setExamples(fetchedData);
            setIsLoading(false);
        });
    }, []);
    const empty = { title: '', url: '', spec: '', code: '' };
    const value = {
        examples,
        isLoading,
        setExamples,
        defaultExample: examples ? examples[0] : empty,
    };
    return <context_1.DataContext.Provider value={value}>{children}</context_1.DataContext.Provider>;
}
const root = client_1.default.createRoot(document.getElementById('root'));
root.render(<DataProvider>
    <App_1.default />
  </DataProvider>);
//# sourceMappingURL=index.js.map